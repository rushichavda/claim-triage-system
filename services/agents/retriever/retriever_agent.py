"""
Retriever Agent using ChromaDB and Qwen embeddings.
Retrieves relevant policy documents for claim denial evaluation.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel, Field

from services.ingest.pdf_parser import PDFParser, ParsedDocument
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.utils import get_logger, get_settings

from .embedding_service import EmbeddingService

logger = get_logger(__name__)


class RetrievedDocument(BaseModel):
    """A retrieved document with relevance score."""

    document_id: UUID
    document_name: str
    document_type: str
    content: str
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Result from retrieval agent."""

    query: str
    retrieved_documents: list[RetrievedDocument]
    retrieval_method: str = "semantic_search"
    total_retrieved: int
    processing_time_ms: float
    audit_events: list[AuditEvent]


class RetrieverAgent:
    """
    Retriever agent for semantic search over policy documents.
    Uses Qwen embeddings + ChromaDB for efficient retrieval.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        chroma_client: Optional[chromadb.Client] = None,
    ) -> None:
        self.settings = get_settings()
        self.logger = logger.bind(agent="retriever")

        # Initialize embedding service
        self.embedding_service = embedding_service or EmbeddingService()

        # Initialize ChromaDB client
        if chroma_client:
            self.chroma_client = chroma_client
        else:
            persist_dir = Path(self.settings.chroma_persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(
                path=str(persist_dir)
            )

        # Get or create policy documents collection
        self.collection_name = "policy_documents"
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Healthcare policy documents for claim appeal evaluation"},
        )

        self.logger.info(
            "retriever_initialized",
            collection=self.collection_name,
            embedding_dim=self.embedding_service.get_embedding_dimension(),
        )

    async def index_policy_document(
        self, document_path: Path, document_name: str, document_type: str = "policy"
    ) -> UUID:
        """
        Index a policy document into the vector store.

        Args:
            document_path: Path to policy document PDF
            document_name: Human-readable document name
            document_type: Type of document (policy, guideline, regulation)

        Returns:
            Document UUID
        """
        self.logger.info("indexing_document", path=str(document_path), name=document_name)

        try:
            # Parse PDF
            parser = PDFParser()
            parsed_doc = parser.parse_pdf(document_path)

            # Generate embeddings for each text span
            texts = [span.text for span in parsed_doc.spans]
            embeddings = self.embedding_service.embed_texts(texts)

            # Prepare metadata for each chunk
            ids = []
            metadatas = []

            for idx, span in enumerate(parsed_doc.spans):
                chunk_id = f"{parsed_doc.document_id}_{idx}"
                ids.append(chunk_id)

                metadatas.append(
                    {
                        "document_id": str(parsed_doc.document_id),
                        "document_name": document_name,
                        "document_type": document_type,
                        "page_number": span.page_number,
                        "paragraph_index": span.paragraph_index,
                        "start_byte": span.start_byte,
                        "end_byte": span.end_byte,
                    }
                )

            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            self.logger.info(
                "document_indexed",
                document_id=str(parsed_doc.document_id),
                chunks=len(texts),
                name=document_name,
            )

            return parsed_doc.document_id

        except Exception as e:
            self.logger.error("indexing_error", path=str(document_path), error=str(e))
            raise

    async def index_policy_chunks(self, policy_doc, chunks: list) -> UUID:
        """
        Index pre-chunked policy document into the vector store.

        Args:
            policy_doc: PolicyDocument object with metadata
            chunks: List of PolicyChunk objects

        Returns:
            Policy document UUID
        """
        from services.shared.schemas.policy import PolicyDocument, PolicyChunk

        self.logger.info("indexing_policy_chunks", policy_name=policy_doc.policy_name, num_chunks=len(chunks))

        try:
            # Extract text from chunks
            texts = [chunk.content for chunk in chunks]

            # Generate embeddings
            embeddings = self.embedding_service.embed_texts(texts)

            # Prepare IDs and metadata
            ids = []
            metadatas = []

            for chunk in chunks:
                chunk_id = f"{policy_doc.policy_id}_{chunk.chunk_index}"
                ids.append(chunk_id)

                metadatas.append({
                    "policy_id": str(policy_doc.policy_id),
                    "policy_name": policy_doc.policy_name,
                    "policy_type": chunk.policy_type,
                    "chunk_index": chunk.chunk_index,
                    "start_byte": chunk.start_byte,
                    "end_byte": chunk.end_byte,
                    "source_file": policy_doc.source_file,
                })

            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            self.logger.info(
                "policy_chunks_indexed",
                policy_id=str(policy_doc.policy_id),
                chunks=len(chunks),
                policy_name=policy_doc.policy_name,
            )

            return policy_doc.policy_id

        except Exception as e:
            self.logger.error("indexing_chunks_error", policy_name=policy_doc.policy_name, error=str(e))
            raise

    async def retrieve_relevant_policies(
        self,
        query: str,
        top_k: int = 10,
        min_relevance_score: float = 0.0,
        claim_id: Optional[UUID] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant policy documents for a query.

        Args:
            query: Query text (e.g., denial reason, claim description)
            top_k: Number of top results to retrieve
            min_relevance_score: Minimum relevance threshold
            claim_id: Optional claim ID for audit trail

        Returns:
            RetrievalResult with retrieved documents
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info("retrieving_policies", query=query[:100], top_k=top_k)

        # Audit event for retrieval start
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.POLICY_RETRIEVED,
                claim_id=claim_id,
                agent_name="retriever_agent",
                description=f"Retrieving relevant policies for query",
                metadata={"query": query[:200], "top_k": top_k},
            )
        )

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_query(query)

            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            # Parse results
            retrieved_docs = []

            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    # Convert distance to similarity score (1 - normalized distance)
                    relevance_score = max(0.0, 1.0 - distance)

                    # Filter by minimum relevance
                    if relevance_score < min_relevance_score:
                        continue

                    metadata = results["metadatas"][0][i]
                    content = results["documents"][0][i]

                    # Handle different metadata structures from different indexing methods
                    # Method 1: index_policy_document (PDF-based)
                    if "document_id" in metadata:
                        document_id = UUID(metadata["document_id"])
                        document_name = metadata["document_name"]
                        document_type = metadata["document_type"]
                    # Method 2: index_policy_chunks (PolicyDocument-based)
                    elif "policy_id" in metadata:
                        document_id = UUID(metadata["policy_id"])
                        document_name = metadata["policy_name"]
                        document_type = metadata.get("policy_type", "policy")
                    # Method 3: Simple indexing (like index_policies_openai.py)
                    else:
                        # Generate a deterministic UUID from policy_name
                        policy_name = metadata.get("policy_name", "unknown")
                        document_id = uuid4()  # Generate new UUID for compatibility
                        document_name = policy_name
                        document_type = "policy"

                    retrieved_doc = RetrievedDocument(
                        document_id=document_id,
                        document_name=document_name,
                        document_type=document_type,
                        content=content,
                        relevance_score=relevance_score,
                        metadata=metadata,
                    )
                    retrieved_docs.append(retrieved_doc)

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.EVIDENCE_RETRIEVED,
                    claim_id=claim_id,
                    agent_name="retriever_agent",
                    description=f"Retrieved {len(retrieved_docs)} relevant policy documents",
                    success=True,
                    metadata={
                        "retrieved_count": len(retrieved_docs),
                        "query": query[:200],
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "retrieval_complete",
                retrieved=len(retrieved_docs),
                processing_time_ms=processing_time_ms,
            )

            return RetrievalResult(
                query=query,
                retrieved_documents=retrieved_docs,
                total_retrieved=len(retrieved_docs),
                processing_time_ms=processing_time_ms,
                audit_events=audit_events,
            )

        except Exception as e:
            self.logger.error("retrieval_error", query=query[:100], error=str(e))

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id,
                    agent_name="retriever_agent",
                    description="Policy retrieval failed",
                    success=False,
                    error_message=str(e),
                )
            )

            raise

    def get_collection_stats(self) -> dict:
        """Get statistics about the indexed collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "embedding_dimension": self.embedding_service.get_embedding_dimension(),
            }
        except Exception as e:
            self.logger.error("stats_error", error=str(e))
            return {}
