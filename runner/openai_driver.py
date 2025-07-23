import os
import asyncio
from typing import Dict, List, Any, Optional
import logging
from openai import AsyncOpenAI
import tiktoken
import httpx

from .base_driver import ChatDriver

logger = logging.getLogger(__name__)


class OpenAIDriver(ChatDriver):
    """OpenAI API driver with async support."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini-2024-07-18"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=httpx.Timeout(30.0, connect=5.0)
        )
        self.model = model
        self._encoding = None
        
    @property
    def encoding(self):
        """Lazy load tokenizer."""
        if self._encoding is None:
            try:
                self._encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback for newer models
                self._encoding = tiktoken.encoding_for_model("gpt-4")
        return self._encoding
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat completion request to OpenAI.
        
        Args:
            messages: Conversation history
            **kwargs: Override parameters (temperature, max_tokens, etc.)
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "seed": kwargs.get("seed", 42),
        }
        
        # Add logprobs if requested
        if kwargs.get("logprobs", False):
            params["logprobs"] = True
            params["top_logprobs"] = kwargs.get("top_logprobs", 5)
        
        try:
            response = await self.client.chat.completions.create(**params)
            
            # Extract response data
            choice = response.choices[0]
            message = choice.message
            
            result = {
                "role": "assistant",
                "content": message.content,
                "tokens": response.usage.total_tokens,
                "model": response.model,
                "finish_reason": choice.finish_reason,
            }
            
            # Add logprobs if available
            if choice.logprobs:
                result["logprobs"] = [
                    {
                        "token": token.token,
                        "logprob": token.logprob,
                        "top_logprobs": [
                            {"token": t.token, "logprob": t.logprob}
                            for t in token.top_logprobs
                        ] if token.top_logprobs else []
                    }
                    for token in choice.logprobs.content
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count using tiktoken."""
        # Format: <|im_start|>role\ncontent<|im_end|>
        total = 0
        for msg in messages:
            total += 4  # Special tokens
            total += len(self.encoding.encode(msg.get("role", "")))
            total += len(self.encoding.encode(msg.get("content", "")))
        total += 2  # Final <|im_start|>assistant
        return total