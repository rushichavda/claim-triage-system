"""
Index policy documents into ChromaDB vector store.
Uses OpenAI text-embedding-3-small for creating embeddings.
"""

import asyncio
from pathlib import Path
from typing import List
import uuid

from services.shared.utils import get_settings, setup_logging, get_logger
from services.agents.retriever.retriever_agent import RetrieverAgent
from services.shared.schemas.policy import PolicyDocument, PolicyChunk

setup_logging(log_level="INFO", json_logs=False)
logger = get_logger(__name__)


class PolicyIndexer:
    """Index policy documents into vector store."""

    def __init__(self):
        self.settings = get_settings()
        self.retriever = RetrieverAgent()
        self.policy_dir = Path(self.settings.policy_docs_path)

    async def index_all_policies(self) -> int:
        """Index all policy documents from policy_docs directory."""

        logger.info("=" * 70)
        logger.info("POLICY DOCUMENT INDEXING")
        logger.info("=" * 70)
        logger.info("")

        # Get all policy files
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

            # Create policy document
            policy_doc = PolicyDocument(
                policy_id=uuid.uuid4(),
                policy_name=policy_file.stem,
                policy_type=self._infer_policy_type(policy_file.stem),
                content=content,
                source_file=str(policy_file),
                effective_date="2024-01-01",
                version="1.0"
            )

            # Chunk the document
            chunks = self._chunk_policy(policy_doc)
            logger.info(f"  Created {len(chunks)} chunks")

            # Index chunks
            await self.retriever.index_policy_chunks(policy_doc, chunks)
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

    def _infer_policy_type(self, filename: str) -> str:
        """Infer policy type from filename."""
        filename_lower = filename.lower()

        if "prior_auth" in filename_lower or "authorization" in filename_lower:
            return "prior_authorization"
        elif "medical_necessity" in filename_lower or "necessity" in filename_lower:
            return "medical_necessity"
        elif "claims_processing" in filename_lower or "processing" in filename_lower:
            return "claims_processing"
        elif "network" in filename_lower or "coverage" in filename_lower:
            return "network_coverage"
        elif "appeal" in filename_lower:
            return "appeals"
        else:
            return "general"

    def _chunk_policy(self, policy_doc: PolicyDocument, chunk_size: int = 800, overlap: int = 200) -> List[PolicyChunk]:
        """
        Chunk policy document into overlapping segments.

        Args:
            policy_doc: Policy document to chunk
            chunk_size: Target size of each chunk in characters (default: 800)
            overlap: Number of characters to overlap between chunks (default: 200)

        Returns:
            List of policy chunks
        """
        content = policy_doc.content
        chunks = []

        # Split by paragraphs first (double newline)
        paragraphs = content.split('\n\n')

        current_chunk = ""
        current_byte_start = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, create new chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                # Create chunk
                chunk = PolicyChunk(
                    chunk_id=uuid.uuid4(),
                    policy_id=policy_doc.policy_id,
                    chunk_index=chunk_index,
                    content=current_chunk.strip(),
                    start_byte=current_byte_start,
                    end_byte=current_byte_start + len(current_chunk.encode('utf-8')),
                    policy_type=policy_doc.policy_type
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_byte_start = current_byte_start + len(current_chunk.encode('utf-8')) - len(overlap_text.encode('utf-8'))
                current_chunk = overlap_text + "\n\n" + para
                chunk_index += 1
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk:
            chunk = PolicyChunk(
                chunk_id=uuid.uuid4(),
                policy_id=policy_doc.policy_id,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                start_byte=current_byte_start,
                end_byte=current_byte_start + len(current_chunk.encode('utf-8')),
                policy_type=policy_doc.policy_type
            )
            chunks.append(chunk)

        return chunks


async def main():
    """Main indexing function."""

    indexer = PolicyIndexer()

    try:
        total_chunks = await indexer.index_all_policies()

        if total_chunks > 0:
            logger.info("✓ Policy indexing successful!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Run tests: pytest tests/")
            logger.info("2. Test retrieval: python scripts/test_retrieval.py")
            logger.info("3. Run full system: docker-compose up")
            return 0
        else:
            logger.error("✗ No policies were indexed")
            return 1

    except Exception as e:
        logger.error(f"✗ Indexing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
