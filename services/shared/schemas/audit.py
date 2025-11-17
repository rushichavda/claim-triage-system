"""
Audit logging schemas for compliance and traceability.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class AuditEventType(str, Enum):
    """Types of auditable events in the system."""

    # Document events
    DOCUMENT_INGESTED = "document_ingested"
    DOCUMENT_PARSED = "document_parsed"

    # Extraction events
    CLAIM_EXTRACTED = "claim_extracted"
    EXTRACTION_VALIDATED = "extraction_validated"

    # Retrieval events
    POLICY_RETRIEVED = "policy_retrieved"
    EVIDENCE_RETRIEVED = "evidence_retrieved"

    # Reasoning events
    DECISION_MADE = "decision_made"
    POLICY_EVALUATED = "policy_evaluated"

    # Citation events
    CITATION_CREATED = "citation_created"
    CITATION_VERIFIED = "citation_verified"
    HALLUCINATION_DETECTED = "hallucination_detected"

    # Appeal events
    APPEAL_DRAFTED = "appeal_drafted"
    APPEAL_SUBMITTED = "appeal_submitted"

    # Human review events
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"

    # Execution events
    CLAIM_UPDATED = "claim_updated"
    SYSTEM_ERROR = "system_error"

    # Security events
    PHI_ACCESSED = "phi_accessed"
    ENCRYPTION_PERFORMED = "encryption_performed"
    AUTHENTICATION_EVENT = "authentication_event"


class AuditEvent(BaseModel):
    """
    Single audit event with full traceability.
    Immutable and append-only for compliance.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    # Entity references
    claim_id: Optional[UUID] = Field(None, description="Related claim ID")
    denial_id: Optional[UUID] = Field(None, description="Related denial ID")
    document_id: Optional[UUID] = Field(None, description="Related document ID")
    agent_name: Optional[str] = Field(None, description="Agent that performed the action")

    # Event details
    description: str = Field(..., description="Human-readable event description")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional event context"
    )

    # Success/failure
    success: bool = Field(default=True, description="Whether event was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # User/system context
    user_id: Optional[str] = Field(None, description="User who triggered event")
    session_id: Optional[UUID] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Source IP address")

    # Data lineage
    parent_event_id: Optional[UUID] = Field(
        None, description="Parent event for chained operations"
    )
    correlation_id: UUID = Field(
        default_factory=uuid4, description="Correlation ID for related events"
    )


class AuditLog(BaseModel):
    """
    Collection of audit events for a specific operation.
    Provides complete audit trail.
    """

    log_id: UUID = Field(default_factory=uuid4, description="Unique log identifier")
    operation_name: str = Field(..., description="Name of the operation")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    events: list[AuditEvent] = Field(default_factory=list, description="Ordered audit events")

    # Summary
    total_events: int = Field(default=0)
    success_count: int = Field(default=0)
    error_count: int = Field(default=0)

    def add_event(self, event: AuditEvent) -> None:
        """Add an event to the log (mutable operation for building)."""
        # Note: We allow this mutation during log construction
        object.__setattr__(self, "events", self.events + [event])
        object.__setattr__(self, "total_events", self.total_events + 1)
        if event.success:
            object.__setattr__(self, "success_count", self.success_count + 1)
        else:
            object.__setattr__(self, "error_count", self.error_count + 1)

    def finalize(self) -> None:
        """Mark the log as completed."""
        object.__setattr__(self, "completed_at", datetime.utcnow())


