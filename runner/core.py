import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import uuid

from .base_driver import ChatDriver
from .scenario_parser import Scenario, Branch, Turn
from .utils import create_output_dir, save_transcript, calculate_cost

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Tracks the state of a single conversation branch."""
    branch_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    turn_count: int = 0
    total_tokens: int = 0
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    

@dataclass
class TurnResult:
    """Results from a single turn execution."""
    primary_response: Dict[str, Any]
    anchor_probe_response: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    

class ConversationRunner:
    """Orchestrates multi-turn conversations with branching and anchor probes."""
    
    def __init__(
        self,
        driver: ChatDriver,
        output_dir: Path,
        config: Dict[str, Any]
    ):
        self.driver = driver
        self.output_dir = output_dir
        self.config = config
        self.run_id = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        
    async def run_scenario(
        self,
        scenario: Scenario,
        evaluators: Optional[List[Any]] = None
    ) -> Dict[str, ConversationState]:
        """
        Run a complete scenario with all branches.
        
        Returns:
            Dict mapping branch_id to final ConversationState
        """
        logger.info(f"Running scenario: {scenario.name}")
        
        # Initialize conversation states for each branch
        states = {}
        for branch in scenario.branches:
            states[branch.id] = ConversationState(branch_id=branch.id)
        
        # Process turns sequentially
        turn_idx = 0
        user_turn_count = 0
        
        for turn in scenario.turns:
            # Check max turns limit
            if turn.role == "user":
                user_turn_count += 1
                if user_turn_count > scenario.max_user_turns:
                    logger.info(f"Reached max user turns ({scenario.max_user_turns})")
                    break
            
            # Process turn for each branch in parallel
            tasks = []
            for branch_id, state in states.items():
                tasks.append(
                    self._process_turn(
                        turn, state, scenario, branch_id, evaluators
                    )
                )
            
            results = await asyncio.gather(*tasks)
            
            # Update states with results
            for (branch_id, turn_result) in results:
                if turn_result:
                    state = states[branch_id]
                    state.turn_count += 1
                    state.metrics.append(turn_result.metrics)
            
            turn_idx += 1
        
        # Save final transcripts
        for branch_id, state in states.items():
            await self._save_branch_transcript(scenario, branch_id, state)
        
        return states
    
    async def _process_turn(
        self,
        turn: Turn,
        state: ConversationState,
        scenario: Scenario,
        branch_id: str,
        evaluators: Optional[List[Any]] = None
    ) -> Tuple[str, Optional[TurnResult]]:
        """Process a single turn for a specific branch."""
        
        # Add non-assistant messages directly
        if turn.role != "assistant":
            state.messages.append({
                "role": turn.role,
                "content": turn.content
            })
            return (branch_id, None)
        
        # Handle assistant turn
        try:
            # Primary model call
            primary_response = await self.driver.chat(
                messages=state.messages,
                **self.config
            )
            
            # Add response to conversation history
            state.messages.append({
                "role": "assistant",
                "content": primary_response["content"]
            })
            state.total_tokens += primary_response.get("tokens", 0)
            
            # Transient anchor probe (don't add to history)
            anchor_response = None
            if scenario.anchor_question:
                probe_messages = state.messages + [
                    {"role": "user", "content": scenario.anchor_question}
                ]
                anchor_response = await self.driver.chat(
                    messages=probe_messages,
                    **self.config
                )
                state.total_tokens += anchor_response.get("tokens", 0)
            
            # Special handling for anchor_guard branch
            if branch_id == "anchor_guard" and scenario.anchor_question:
                # Append anchor Q&A to history
                state.messages.append({
                    "role": "user",
                    "content": scenario.anchor_question
                })
                state.messages.append({
                    "role": "assistant",
                    "content": anchor_response["content"] if anchor_response else ""
                })
            
            # Evaluate responses
            metrics = {
                "turn": state.turn_count,
                "branch": branch_id,
                "tokens_primary": primary_response.get("tokens", 0),
                "tokens_probe": anchor_response.get("tokens", 0) if anchor_response else 0,
            }
            
            if evaluators:
                for evaluator in evaluators:
                    eval_metrics = await evaluator.evaluate(
                        primary_response=primary_response,
                        anchor_response=anchor_response,
                        scenario=scenario,
                        state=state
                    )
                    metrics.update(eval_metrics)
            
            result = TurnResult(
                primary_response=primary_response,
                anchor_probe_response=anchor_response,
                metrics=metrics
            )
            
            return (branch_id, result)
            
        except Exception as e:
            logger.error(f"Error in turn processing: {e}")
            return (branch_id, None)
    
    async def _save_branch_transcript(
        self,
        scenario: Scenario,
        branch_id: str,
        state: ConversationState
    ):
        """Save conversation transcript for a branch."""
        transcript_data = {
            "run_id": self.run_id,
            "scenario": scenario.name,
            "branch": branch_id,
            "model": self.config.get("model", "unknown"),
            "messages": state.messages,
            "metrics": state.metrics,
            "total_tokens": state.total_tokens,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        filename = f"{scenario.name}_{branch_id}_{self.run_id}.jsonl"
        filepath = self.output_dir / "transcripts" / filename
        
        await save_transcript(filepath, transcript_data)