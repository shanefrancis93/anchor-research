"""
AI client for making API calls to OpenAI and Anthropic models.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import openai
import anthropic
from datetime import datetime

class AIClient:
    """Unified client for OpenAI and Anthropic APIs."""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize OpenAI client
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            self.openai_client = openai.OpenAI(api_key=openai_key)
        
        # Initialize Anthropic client
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
    
    async def get_response(self, model: str, messages: List[Dict[str, str]], 
                          temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Get a response from the specified AI model.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3-opus')
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            AI response text
        """
        try:
            if model.startswith('gpt-') or model.startswith('o1-'):
                return await self._get_openai_response(model, messages, temperature, max_tokens)
            elif model.startswith('claude-'):
                return await self._get_anthropic_response(model, messages, temperature, max_tokens)
            else:
                raise ValueError(f"Unsupported model: {model}")
        except Exception as e:
            print(f"Error getting AI response: {e}")
            return f"[Error: {str(e)}]"
    
    async def _get_openai_response(self, model: str, messages: List[Dict[str, str]], 
                                  temperature: float, max_tokens: int) -> str:
        """Get response from OpenAI API."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            # Run the synchronous API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _get_anthropic_response(self, model: str, messages: List[Dict[str, str]], 
                                     temperature: float, max_tokens: int) -> str:
        """Get response from Anthropic API."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            # Convert messages format for Anthropic
            system_message = ""
            anthropic_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    anthropic_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Run the synchronous API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.anthropic_client.messages.create(
                    model=model,
                    system=system_message,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
            
            return response.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def is_model_available(self, model: str) -> bool:
        """Check if a model is available based on configured API keys."""
        if model.startswith('gpt-') or model.startswith('o1-'):
            return self.openai_client is not None
        elif model.startswith('claude-'):
            return self.anthropic_client is not None
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models based on configured API keys."""
        models = []
        
        if self.openai_client:
            models.extend([
                'gpt-4',
                'gpt-4-turbo',
                'gpt-3.5-turbo',
                'o1-preview',
                'o1-mini'
            ])
        
        if self.anthropic_client:
            models.extend([
                'claude-3-5-sonnet-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ])
        
        return models

# Global AI client instance
ai_client = AIClient()
