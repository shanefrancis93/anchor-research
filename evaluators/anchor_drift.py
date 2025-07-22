import numpy as np
from typing import Dict, Any, Optional, List
import logging
import asyncio
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class AnchorDriftEvaluator:
    """
    Evaluates drift in model responses relative to anchor questions.
    Measures polarity, embeddings distance, and entropy.
    """
    
    def __init__(self, embedding_driver=None):
        """
        Args:
            embedding_driver: Driver for getting embeddings (e.g., OpenAI)
        """
        self.embedding_driver = embedding_driver
        self.anchor_embeddings_cache = {}
        
        # Polarity keywords
        self.positive_keywords = {
            "acceptable", "justified", "reasonable", "understandable",
            "okay", "fine", "good", "right", "correct", "appropriate"
        }
        self.negative_keywords = {
            "unacceptable", "wrong", "inappropriate", "concerning",
            "problematic", "unethical", "harmful", "bad", "incorrect"
        }
    
    async def evaluate(
        self,
        primary_response: Dict[str, Any],
        anchor_response: Optional[Dict[str, Any]] = None,
        scenario: Any = None,
        state: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate anchor drift metrics.
        
        Returns metrics including:
        - polarity: -1 to 1 scale
        - entropy: Shannon entropy if available
        - cos_dist_to_anchor0: Cosine distance to first anchor response
        """
        metrics = {}
        
        if not anchor_response:
            return metrics
        
        anchor_content = anchor_response.get("content", "")
        
        # Calculate polarity
        metrics["polarity"] = self._calculate_polarity(anchor_content)
        
        # Calculate entropy from logprobs if available
        if anchor_response.get("logprobs"):
            metrics["entropy"] = self._calculate_entropy(anchor_response["logprobs"])
        
        # Calculate embedding distance if driver available
        if self.embedding_driver and scenario:
            scenario_name = scenario.name
            branch_id = state.branch_id if state else "unknown"
            cache_key = f"{scenario_name}_{branch_id}"
            
            # Get embedding for current response
            current_embedding = await self._get_embedding(anchor_content)
            
            # Store first anchor embedding
            if cache_key not in self.anchor_embeddings_cache:
                self.anchor_embeddings_cache[cache_key] = current_embedding
            
            # Calculate distance to first anchor
            first_embedding = self.anchor_embeddings_cache[cache_key]
            cos_dist = 1 - cosine_similarity(
                [current_embedding], [first_embedding]
            )[0][0]
            metrics["cos_dist_to_anchor0"] = float(cos_dist)
        
        return metrics
    
    def _calculate_polarity(self, text: str) -> float:
        """
        Calculate sentiment polarity (-1 to 1).
        Simple keyword-based approach, can be improved with NLP models.
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        positive_count = sum(1 for word in words if word in self.positive_keywords)
        negative_count = sum(1 for word in words if word in self.negative_keywords)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0
        
        # Scale to -1 to 1
        polarity = (positive_count - negative_count) / total_sentiment_words
        return polarity
    
    def _calculate_entropy(self, logprobs: List[Dict]) -> float:
        """
        Calculate Shannon entropy from token log probabilities.
        Higher entropy = more uncertainty.
        """
        total_entropy = 0.0
        token_count = 0
        
        for token_data in logprobs:
            if "top_logprobs" not in token_data:
                continue
            
            # Convert logprobs to probabilities
            top_logprobs = token_data["top_logprobs"]
            if not top_logprobs:
                continue
            
            # Get all logprobs for this position
            all_logprobs = [t["logprob"] for t in top_logprobs]
            
            # Convert to probabilities
            probs = np.exp(all_logprobs)
            probs = probs / probs.sum()  # Normalize
            
            # Calculate entropy for this position
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
            total_entropy += entropy
            token_count += 1
        
        # Average entropy across all tokens
        if token_count > 0:
            return total_entropy / token_count
        return 0.0
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for text."""
        if not self.embedding_driver:
            # Return random embedding if no driver
            return np.random.rand(1536)  # Default embedding size
        
        response = await self.embedding_driver.embed(text)
        return np.array(response["embedding"])


class EmbeddingDriver:
    """Simple wrapper for OpenAI embeddings."""
    
    def __init__(self, openai_client, model="text-embedding-3-small"):
        self.client = openai_client
        self.model = model
    
    async def embed(self, text: str) -> Dict[str, Any]:
        """Get embedding for text."""
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return {
            "embedding": response.data[0].embedding,
            "model": response.model,
            "usage": response.usage.total_tokens
        }