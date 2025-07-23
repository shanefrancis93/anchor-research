import os
import asyncio
from typing import Dict, List, Any, Optional
import logging
from anthropic import AsyncAnthropic
import httpx

from .base_driver import ChatDriver

logger = logging.getLogger(__name__)


class AnthropicDriver(ChatDriver):
    """Anthropic API driver with async support."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            timeout=httpx.Timeout(30.0, connect=5.0)
        )
        self.model = model
        
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat completion request to Anthropic.
        
        Args:
            messages: Conversation history
            **kwargs: Override parameters (temperature, max_tokens, etc.)
        """
        # Extract system message if present
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        params = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
        }
        
        if system_message:
            params["system"] = system_message
        
        try:
            response = await self.client.messages.create(**params)
            
            # Calculate total tokens (approximation)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            result = {
                "role": "assistant",
                "content": response.content[0].text,
                "tokens": total_tokens,
                "model": response.model,
                "finish_reason": response.stop_reason,
                "logprobs": None,  # Anthropic doesn't support logprobs
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for Anthropic.
        Uses rough approximation: 1 token ≈ 4 characters
        """
        total_chars = 0
        for msg in messages:
            total_chars += len(msg.get("role", ""))
            total_chars += len(msg.get("content", ""))
        return int(total_chars / 4)