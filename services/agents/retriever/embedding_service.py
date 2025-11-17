"""
Embedding service using OpenAI's text-embedding models.
Handles embedding generation for documents and queries.
"""

from typing import Optional

from openai import OpenAI

from services.shared.utils import get_logger, get_settings

logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI's embedding models.
    Uses text-embedding-3-small by default (1536 dimensions, cost-effective).
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.embedding_model
        self.logger = logger.bind(component="embedding_service")

        self.logger.info("initializing_openai_embeddings", model=self.model_name)

        try:
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.settings.openai_api_key)

            # Set embedding dimension based on model
            # text-embedding-3-small: 1536, text-embedding-3-large: 3072
            if "large" in self.model_name:
                self.embedding_dim = 3072
            else:
                self.embedding_dim = 1536

            self.logger.info(
                "openai_embeddings_initialized",
                model=self.model_name,
                dimension=self.embedding_dim,
            )

        except Exception as e:
            self.logger.error("embedding_service_init_error", error=str(e))
            raise RuntimeError(f"Failed to initialize OpenAI embedding service: {e}") from e

    def embed_texts(self, texts: list[str], batch_size: Optional[int] = None) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for processing (not used with OpenAI, kept for compatibility)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            self.logger.debug("embedding_texts", count=len(texts))

            # Generate embeddings using OpenAI API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            return embeddings

        except Exception as e:
            self.logger.error("embedding_generation_error", error=str(e))
            raise RuntimeError(f"Failed to generate embeddings: {e}") from e

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a single query.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        try:
            # Generate embedding using OpenAI API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=query
            )

            return response.data[0].embedding

        except Exception as e:
            self.logger.error("query_embedding_error", error=str(e))
            raise RuntimeError(f"Failed to generate query embedding: {e}") from e

    def embed_document(self, document: str) -> list[float]:
        """
        Generate embedding for a document.

        Args:
            document: Document text

        Returns:
            Embedding vector
        """
        try:
            # Generate embedding using OpenAI API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=document
            )

            return response.data[0].embedding

        except Exception as e:
            self.logger.error("document_embedding_error", error=str(e))
            raise RuntimeError(f"Failed to generate document embedding: {e}") from e

    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings."""
        return self.embedding_dim

    def compute_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        try:
            # Compute dot product
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

            # Compute magnitudes
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5

            # Compute cosine similarity
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)

            return float(similarity)

        except Exception as e:
            self.logger.error("similarity_computation_error", error=str(e))
            return 0.0
