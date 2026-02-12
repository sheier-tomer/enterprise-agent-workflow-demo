"""
Embedding providers for converting text to vectors.
Supports: OpenAI, Sentence Transformers, and Mock mode.
"""

import hashlib
import logging
import random
from abc import ABC, abstractmethod
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing without API calls.
    Generates deterministic pseudo-random vectors based on text hash.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        logger.info(f"Initialized MockEmbeddingProvider (dim={dimension})")

    def _text_to_seed(self, text: str) -> int:
        """Convert text to deterministic seed for reproducibility."""
        return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)

    async def embed_text(self, text: str) -> List[float]:
        """Generate deterministic mock embedding."""
        seed = self._text_to_seed(text)
        rng = random.Random(seed)
        
        # Generate random vector with unit length
        vector = [rng.gauss(0, 1) for _ in range(self._dimension)]
        
        # Normalize to unit length
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
        
        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for batch."""
        return [await self.embed_text(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Sentence Transformers embedding provider.
    Uses local models, no API key required.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self._dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Initialized SentenceTransformer: {model_name} (dim={self._dimension})")
        except ImportError:
            logger.error("sentence-transformers not installed, falling back to mock")
            raise ImportError("sentence-transformers package required")

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using Sentence Transformers."""
        # Truncate to reasonable length
        text = text[:5000]
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch."""
        # Truncate all texts
        texts = [t[:5000] for t in texts]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = model
            # text-embedding-3-small has 1536 dimensions by default
            # text-embedding-ada-002 has 1536 dimensions
            self._dimension = 1536 if "ada" in model or "3-small" in model else 1536
            logger.info(f"Initialized OpenAI embeddings: {model} (dim={self._dimension})")
        except ImportError:
            logger.error("openai package not installed, falling back to mock")
            raise ImportError("openai package required")

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        text = text.replace("\n", " ")[:8000]  # OpenAI limit
        
        response = await self.client.embeddings.create(
            input=[text],
            model=self.model
        )
        
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch."""
        texts = [t.replace("\n", " ")[:8000] for t in texts]
        
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dimension


def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory function to get the configured embedding provider.
    
    Returns:
        EmbeddingProvider instance based on settings
    """
    provider_type = settings.embedding_provider.lower()
    
    if provider_type == "mock" or settings.use_mock_llm:
        return MockEmbeddingProvider(dimension=settings.embedding_dimension)
    
    elif provider_type == "sentence-transformers":
        try:
            return SentenceTransformerProvider(model_name=settings.embedding_model)
        except ImportError:
            logger.warning("Sentence Transformers not available, using mock")
            return MockEmbeddingProvider(dimension=settings.embedding_dimension)
    
    elif provider_type == "openai":
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, using mock embeddings")
            return MockEmbeddingProvider(dimension=settings.embedding_dimension)
        
        try:
            return OpenAIEmbeddingProvider(model="text-embedding-3-small")
        except ImportError:
            logger.warning("OpenAI package not available, using mock")
            return MockEmbeddingProvider(dimension=settings.embedding_dimension)
    
    else:
        logger.warning(f"Unknown embedding provider: {provider_type}, using mock")
        return MockEmbeddingProvider(dimension=settings.embedding_dimension)
