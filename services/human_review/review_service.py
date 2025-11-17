"""
Review Service - backend logic for human review.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from services.shared.schemas.appeal import Appeal, AppealDraft, AppealStatus
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.utils import get_logger

logger = get_logger(__name__)


class ReviewDecision(str, Enum):
    """Human review decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATIONS_REQUIRED = "modifications_required"


class ReviewResult(BaseModel):
    """Result of human review."""

    decision: ReviewDecision
    reviewed_by: str
    review_notes: Optional[str] = None
    modifications_made: bool = False
    modified_appeal_text: Optional[str] = None
    audit_events: list[AuditEvent]


class ReviewService:
    """Service for managing human review workflow."""

    def __init__(self) -> None:
        self.logger = logger.bind(component="review_service")

    async def submit_for_review(
        self, appeal_draft: AppealDraft, claim_id: Optional[UUID] = None
    ) -> None:
        """
        Submit appeal draft for human review.

        Args:
            appeal_draft: Draft to review
            claim_id: Optional claim ID
        """
        self.logger.info(
            "submitting_for_review",
            draft_id=str(appeal_draft.draft_id),
            citation_coverage=appeal_draft.citation_coverage,
            hallucination_risk=appeal_draft.hallucination_risk_score,
        )

        # In production, this would:
        # 1. Store draft in database
        # 2. Notify human reviewers
        # 3. Create review queue entry

    async def record_review_decision(
        self,
        appeal_draft: AppealDraft,
        decision: ReviewDecision,
        reviewed_by: str,
        review_notes: Optional[str] = None,
        modified_appeal_text: Optional[str] = None,
        claim_id: Optional[UUID] = None,
    ) -> ReviewResult:
        """
        Record a human review decision.

        Args:
            appeal_draft: Draft being reviewed
            decision: Review decision
            reviewed_by: Reviewer identifier
            review_notes: Optional review notes
            modified_appeal_text: Modified appeal text if changes made
            claim_id: Optional claim ID

        Returns:
            ReviewResult with audit trail
        """
        audit_events = []

        self.logger.info(
            "recording_review",
            draft_id=str(appeal_draft.draft_id),
            decision=decision.value,
            reviewed_by=reviewed_by,
        )

        # Determine if modifications were made
        modifications_made = modified_appeal_text is not None and modified_appeal_text != appeal_draft.appeal_text

        # Create audit event
        if decision == ReviewDecision.APPROVED:
            event_type = AuditEventType.HUMAN_APPROVED
            description = f"Appeal approved by {reviewed_by}"
        elif decision == ReviewDecision.REJECTED:
            event_type = AuditEventType.HUMAN_REJECTED
            description = f"Appeal rejected by {reviewed_by}"
        else:
            event_type = AuditEventType.HUMAN_REVIEW_REQUESTED
            description = f"Modifications required by {reviewed_by}"

        audit_events.append(
            AuditEvent(
                event_type=event_type,
                claim_id=claim_id or appeal_draft.claim_id,
                denial_id=appeal_draft.denial_id,
                agent_name="human_reviewer",
                user_id=reviewed_by,
                description=description,
                success=(decision == ReviewDecision.APPROVED),
                metadata={
                    "decision": decision.value,
                    "modifications_made": modifications_made,
                    "review_notes": review_notes,
                },
            )
        )

        result = ReviewResult(
            decision=decision,
            reviewed_by=reviewed_by,
            review_notes=review_notes,
            modifications_made=modifications_made,
            modified_appeal_text=modified_appeal_text,
            audit_events=audit_events,
        )

        self.logger.info(
            "review_recorded",
            draft_id=str(appeal_draft.draft_id),
            decision=decision.value,
            modifications=modifications_made,
        )

        return result

    def create_appeal_from_draft(
        self, appeal_draft: AppealDraft, review_result: ReviewResult
    ) -> Appeal:
        """
        Create final Appeal from reviewed draft.

        Args:
            appeal_draft: Approved draft
            review_result: Review result

        Returns:
            Appeal object
        """
        # Use modified text if provided, otherwise use original
        final_text = (
            review_result.modified_appeal_text
            if review_result.modifications_made
            else appeal_draft.appeal_text
        )

        appeal = Appeal(
            draft_id=appeal_draft.draft_id,
            claim_id=appeal_draft.claim_id,
            status=AppealStatus.APPROVED if review_result.decision == ReviewDecision.APPROVED else AppealStatus.REJECTED,
            final_appeal_text=final_text,
            final_citations=appeal_draft.citations,
            reviewed_by=review_result.reviewed_by,
            reviewed_at=datetime.utcnow(),
            review_notes=review_result.review_notes,
            modifications_made=review_result.modifications_made,
            audit_log_id=appeal_draft.draft_id,  # Link to audit log
        )

        return appeal
