"""
Conversation state management for anchor research tool.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class ConversationState:
    """Tracks the state of an ongoing conversation session."""
    
    session_id: str
    scenario_id: str
    model: str
    branch: str = "baseline"
    current_turn: int = 0
    max_turns: int = 6
    messages: List[Dict[str, Any]] = field(default_factory=list)
    anchor_responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'turn': self.current_turn
        }
        self.messages.append(message)
        
        if role == 'user':
            self.current_turn += 1
    
    def add_anchor_response(self, turn: int, question: str, response: str) -> None:
        """Add an anchor question response."""
        if str(turn) not in self.anchor_responses:
            self.anchor_responses[str(turn)] = {}
        
        self.anchor_responses[str(turn)][question] = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_progress(self) -> float:
        """Get conversation progress as percentage."""
        if self.max_turns == 0:
            return 0.0
        return min(self.current_turn / self.max_turns, 1.0)
    
    def is_complete(self) -> bool:
        """Check if conversation is complete."""
        return self.current_turn >= self.max_turns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'scenario_id': self.scenario_id,
            'model': self.model,
            'branch': self.branch,
            'current_turn': self.current_turn,
            'max_turns': self.max_turns,
            'messages': self.messages,
            'anchor_responses': self.anchor_responses,
            'metrics': self.metrics,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'progress': self.get_progress()
        }
