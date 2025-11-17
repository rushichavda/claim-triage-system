"""
Appeal-related schemas for drafting and submission.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict

from .citation import Citation


class AppealStatus(str, Enum):
    """Status of an appeal through its lifecycle."""

    DRAFTED = "drafted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    DENIED = "denied"


class AppealDraft(BaseModel):
    """
    Draft appeal with citations and audit trail.
    Every claim must be backed by verifiable citations.
    """

    draft_id: UUID = Field(default_factory=uuid4, description="Unique draft identifier")
    claim_id: UUID = Field(..., description="Reference to original claim")
    denial_id: UUID = Field(..., description="Reference to denial")
    decision_id: UUID = Field(..., description="Reference to decision")

    # Appeal content
    appeal_text: str = Field(..., description="Full appeal letter text")
    appeal_summary: str = Field(..., description="Brief summary of appeal")

    # Citations - CRITICAL for audit trail
    citations: list[Citation] = Field(
        default_factory=list, description="All citations supporting appeal claims"
    )

    # Structured arguments
    denial_reason_challenged: str = Field(..., description="Which denial reason is challenged")
    key_arguments: list[str] = Field(..., description="Key arguments in appeal")
    policy_violations: list[str] = Field(
        default_factory=list, description="Claimed policy violations by payor"
    )

    # Evidence summary
    supporting_documents: list[UUID] = Field(
        default_factory=list, description="Document IDs attached as evidence"
    )
    clinical_rationale: Optional[str] = Field(
        None, description="Clinical justification if applicable"
    )

    # Metadata
    drafted_at: datetime = Field(default_factory=datetime.utcnow)
    drafted_by: str = Field(default="appeal_drafter_agent")
    model_version: str = Field(..., description="Model version used for drafting")

    # Quality metrics
    citation_coverage: float = Field(
        ..., ge=0.0, le=1.0, description="Percentage of claims with citations"
    )
    hallucination_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Estimated hallucination risk (lower is better)"
    )
    avg_citation_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Average confidence across all citations"
    )

    # Audit block - compact summary for human review
    audit_summary: str = Field(
        ..., description="Human-readable audit summary showing citation coverage"
    )


class Appeal(BaseModel):
    """
    Final appeal after human review and approval.
    Includes execution status.
    """

    appeal_id: UUID = Field(default_factory=uuid4, description="Unique appeal identifier")
    draft_id: UUID = Field(..., description="Reference to draft")
    claim_id: UUID = Field(..., description="Reference to claim")

    # Appeal status
    status: AppealStatus = Field(default=AppealStatus.DRAFTED)

    # Final content (may be modified from draft)
    final_appeal_text: str = Field(..., description="Final approved appeal text")
    final_citations: list[Citation] = Field(..., description="Final citations")

    # Review information
    reviewed_by: Optional[str] = Field(None, description="Human reviewer ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    review_notes: Optional[str] = Field(None, description="Reviewer comments")
    modifications_made: bool = Field(
        default=False, description="Whether human made modifications"
    )

    # Submission information
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")
    submitted_by: Optional[str] = Field(None, description="Who submitted")
    submission_method: Optional[str] = Field(
        None, description="How submitted (API, portal, fax, etc.)"
    )
    submission_reference: Optional[str] = Field(
        None, description="External submission reference number"
    )

    # Outcome tracking
    payor_response_date: Optional[datetime] = Field(None)
    final_outcome: Optional[str] = Field(None, description="Final outcome from payor")

    # Audit trail reference
    audit_log_id: UUID = Field(..., description="Reference to complete audit log")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
