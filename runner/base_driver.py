from typing import Protocol, Dict, List, Optional, Any
from abc import abstractmethod


class ChatDriver(Protocol):
    """Base protocol for all chat model drivers."""
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dict containing:
                - role: "assistant"
                - content: The model's response
                - tokens: Total tokens used (input + output)
                - logprobs: Token log probabilities (if available)
                - model: The model ID used
        """
        pass
    
    @abstractmethod
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages."""
        pass