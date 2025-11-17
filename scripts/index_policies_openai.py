"""
Index policy documents using OpenAI embeddings (no heavy model download needed).
"""

import asyncio
from pathlib import Path
from typing import List
import uuid
import chromadb
from openai import AsyncOpenAI
import os

from services.shared.utils import get_settings, setup_logging, get_logger

setup_logging(log_level="INFO", json_logs=False)
logger = get_logger(__name__)


class SimplePolicyIndexer:
    """Index policies using OpenAI embeddings."""

    def __init__(self):
        self.settings = get_settings()
        self.policy_dir = Path(self.settings.policy_docs_path)
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize ChromaDB in embedded mode
        self.chroma_client = chromadb.PersistentClient(
            path=str(Path(self.settings.chroma_persist_directory))
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="policy_documents",
            metadata={"description": "Healthcare policy documents"}
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def _chunk_text(self, content: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
        """
        Chunk text into overlapping segments.

        Args:
            content: Full text content
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        paragraphs = content.split('\n\n')

        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, create new chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def index_all_policies(self) -> int:
        """Index all policy documents."""
        logger.info("=" * 70)
        logger.info("POLICY DOCUMENT INDEXING (OpenAI Embeddings)")
        logger.info("=" * 70)
        logger.info("")

        policy_files = list(self.policy_dir.glob("*.txt"))

        if not policy_files:
            logger.warning(f"No policy files found in {self.policy_dir}")
            return 0

        logger.info(f"Found {len(policy_files)} policy documents to index")
        logger.info("-" * 70)

        total_chunks = 0

        for policy_file in policy_files:
            logger.info(f"Processing: {policy_file.name}")

            # Read policy content
            with open(policy_file, 'r') as f:
                content = f.read()

            # Overlapping chunking (chunk_size=800, overlap=200)
            chunks = self._chunk_text(content, chunk_size=800, overlap=200)

            logger.info(f"  Created {len(chunks)} chunks")

            # Generate embeddings and index
            for i, chunk_text in enumerate(chunks):
                # Generate embedding
                embedding = await self.generate_embedding(chunk_text)

                # Add to ChromaDB
                chunk_id = f"{policy_file.stem}_chunk_{i}"
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk_text],
                    metadatas=[{
                        "policy_name": policy_file.stem,
                        "chunk_index": i,
                        "source_file": str(policy_file)
                    }]
                )

            total_chunks += len(chunks)
            logger.info(f"  ✓ Indexed: {policy_file.name}")

        logger.info("")
        logger.info("=" * 70)
        logger.info("INDEXING COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"Total documents: {len(policy_files)}")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info("")

        return total_chunks


async def main():
    """Main indexing function."""
    indexer = SimplePolicyIndexer()

    try:
        total_chunks = await indexer.index_all_policies()

        if total_chunks > 0:
            logger.info("✓ Policy indexing successful!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Run tests: pytest tests/unit/")
            logger.info("2. Test system outputs")
            return 0
        else:
            logger.error("✗ No policies were indexed")
            return 1

    except Exception as e:
        logger.error(f"✗ Indexing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
