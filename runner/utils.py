import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


async def create_output_dir(base_dir: Path) -> Path:
    """Create timestamped output directory."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    output_dir = base_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "transcripts").mkdir(exist_ok=True)
    return output_dir


async def save_transcript(filepath: Path, data: Dict[str, Any]):
    """Save transcript data as JSONL."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(filepath, 'a') as f:
        await f.write(json.dumps(data) + '\n')


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_config: Dict[str, Dict[str, float]]
) -> float:
    """Calculate cost in USD for token usage."""
    if model not in cost_config:
        return 0.0
    
    rates = cost_config[model]
    input_cost = (input_tokens / 1000) * rates.get("input", 0)
    output_cost = (output_tokens / 1000) * rates.get("output", 0)
    
    return input_cost + output_cost


def estimate_scenario_cost(
    scenario,
    models: list,
    cost_config: Dict[str, Dict[str, float]]
) -> float:
    """Estimate total cost for running a scenario."""
    # Rough estimation: assume 500 tokens per turn average
    avg_tokens_per_turn = 500
    num_turns = len([t for t in scenario.turns if t.role == "assistant"])
    num_branches = len(scenario.branches)
    
    total_cost = 0.0
    for model in models:
        # Each branch, each turn, plus anchor probes
        total_turns = num_turns * num_branches * 2  # x2 for anchor probes
        total_tokens = total_turns * avg_tokens_per_turn
        
        # Assume 70% input, 30% output
        input_tokens = int(total_tokens * 0.7)
        output_tokens = int(total_tokens * 0.3)
        
        total_cost += calculate_cost(model, input_tokens, output_tokens, cost_config)
    
    return total_cost