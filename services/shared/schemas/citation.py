"""
Citation and source tracking schemas for audit trail.
Every claim in appeals must link to verifiable source spans.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class SourceDocument(BaseModel):
    """Metadata for source documents (policy docs, claim denials, etc.)."""

    model_config = ConfigDict(frozen=True)

    document_id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    document_type: str = Field(..., description="Type of document (policy, denial, clinical)")
    document_path: str = Field(..., description="Path or URI to document")
    document_name: str = Field(..., description="Human-readable document name")

    # Content metadata
    total_bytes: int = Field(..., description="Total document size in bytes")
    total_pages: Optional[int] = Field(None, description="Number of pages (for PDFs)")
    content_hash: str = Field(..., description="SHA-256 hash of document content")

    # Processing metadata
    ingested_at: datetime = Field(
        default_factory=datetime.utcnow, description="Document ingestion timestamp"
    )
    version: str = Field(default="1.0", description="Document version")


class CitationSpan(BaseModel):
    """Exact byte-level or paragraph-level span within a source document."""

    model_config = ConfigDict(frozen=True)

    document_id: UUID = Field(..., description="Reference to source document")

    # Byte-level span (primary)
    start_byte: Optional[int] = Field(None, description="Start byte offset")
    end_byte: Optional[int] = Field(None, description="End byte offset (exclusive)")

    # Page/paragraph-level span (fallback for complex PDFs)
    page_number: Optional[int] = Field(None, description="Page number (1-indexed)")
    paragraph_index: Optional[int] = Field(None, description="Paragraph index on page")

    # Extracted text for verification
    extracted_text: str = Field(..., description="Actual text from source")

    # Confidence and validation
    extraction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in extraction accuracy"
    )


class Citation(BaseModel):
    """
    Links a claim or statement in an appeal to its verifiable source.
    Critical for hallucination prevention and audit compliance.
    """

    model_config = ConfigDict(frozen=True)

    citation_id: UUID = Field(default_factory=uuid4, description="Unique citation identifier")

    # Link to generated content
    claim_text: str = Field(..., description="The claim or statement being cited")
    claim_token_range: Optional[tuple[int, int]] = Field(
        None, description="Token range in generated text (start, end)"
    )

    # Source reference
    source_span: CitationSpan = Field(..., description="Exact source span")

    # Verification
    verified: bool = Field(default=False, description="Whether citation has been verified")
    verification_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Semantic similarity score between claim and source"
    )
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")

    # Metadata
    citation_type: str = Field(
        default="evidence", description="Type of citation (evidence, policy, clinical)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Citation creation timestamp"
    )
