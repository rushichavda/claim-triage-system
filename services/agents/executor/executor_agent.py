"""
Executor Agent implementation.
Handles writeback to claims system with guarded permissions and audit trail.
For demo/prototype, this simulates writeback operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from services.shared.schemas.appeal import Appeal, AppealStatus
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.utils import get_logger

logger = get_logger(__name__)


class ExecutionAction(str, Enum):
    """Types of execution actions."""

    SUBMIT_APPEAL = "submit_appeal"
    UPDATE_CLAIM_STATUS = "update_claim_status"
    NOTIFY_STAKEHOLDERS = "notify_stakeholders"
    ARCHIVE_CASE = "archive_case"


class ExecutionPermission(str, Enum):
    """Permission levels for execution."""

    READ_ONLY = "read_only"
    WRITE_APPEALS = "write_appeals"
    ADMIN = "admin"


class ExecutionResult(BaseModel):
    """Result of execution operation."""

    success: bool
    action: ExecutionAction
    appeal_id: Optional[UUID] = None
    execution_reference: Optional[str] = None
    message: str
    audit_events: list[AuditEvent]
    processing_time_ms: float


class ExecutorAgent:
    """
    Executor Agent with guarded permissions.
    Simulates writeback to external claims system with safety checks.
    """

    def __init__(self, permission_level: ExecutionPermission = ExecutionPermission.WRITE_APPEALS) -> None:
        self.permission_level = permission_level
        self.logger = logger.bind(agent="executor", permission=permission_level.value)

        self.logger.info("executor_initialized", permission=permission_level.value)

    async def execute_appeal_submission(
        self,
        appeal: Appeal,
        approved_by: str,
        claim_id: Optional[UUID] = None,
    ) -> ExecutionResult:
        """
        Execute appeal submission to external system.

        Args:
            appeal: Approved appeal to submit
            approved_by: User who approved the appeal
            claim_id: Optional claim ID for audit

        Returns:
            ExecutionResult with submission status
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info(
            "executing_appeal_submission",
            appeal_id=str(appeal.appeal_id),
            approved_by=approved_by,
        )

        # Check permissions
        if self.permission_level == ExecutionPermission.READ_ONLY:
            error_msg = "Insufficient permissions: READ_ONLY cannot submit appeals"
            self.logger.error("permission_denied", message=error_msg)

            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id or appeal.claim_id,
                    agent_name="executor_agent",
                    description="Appeal submission blocked: insufficient permissions",
                    success=False,
                    error_message=error_msg,
                    metadata={"permission": self.permission_level.value},
                )
            )

            return ExecutionResult(
                success=False,
                action=ExecutionAction.SUBMIT_APPEAL,
                message=error_msg,
                audit_events=audit_events,
                processing_time_ms=0.0,
            )

        # Audit event for submission attempt
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.APPEAL_SUBMITTED,
                claim_id=claim_id or appeal.claim_id,
                agent_name="executor_agent",
                description=f"Attempting to submit appeal (approved by {approved_by})",
                metadata={
                    "appeal_id": str(appeal.appeal_id),
                    "approved_by": approved_by,
                    "permission": self.permission_level.value,
                },
            )
        )

        try:
            # Simulate appeal submission
            execution_reference = await self._simulate_appeal_submission(appeal)

            # Update appeal status (in production, this would update database)
            object.__setattr__(appeal, "status", AppealStatus.SUBMITTED)
            object.__setattr__(appeal, "submitted_at", datetime.utcnow())
            object.__setattr__(appeal, "submitted_by", approved_by)
            object.__setattr__(appeal, "submission_reference", execution_reference)

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.APPEAL_SUBMITTED,
                    claim_id=claim_id or appeal.claim_id,
                    agent_name="executor_agent",
                    description=f"Appeal submitted successfully: {execution_reference}",
                    success=True,
                    metadata={
                        "appeal_id": str(appeal.appeal_id),
                        "execution_reference": execution_reference,
                        "approved_by": approved_by,
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "appeal_submitted",
                appeal_id=str(appeal.appeal_id),
                reference=execution_reference,
                processing_time_ms=processing_time_ms,
            )

            return ExecutionResult(
                success=True,
                action=ExecutionAction.SUBMIT_APPEAL,
                appeal_id=appeal.appeal_id,
                execution_reference=execution_reference,
                message=f"Appeal submitted successfully: {execution_reference}",
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            self.logger.error("appeal_submission_error", appeal_id=str(appeal.appeal_id), error=str(e))

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id or appeal.claim_id,
                    agent_name="executor_agent",
                    description="Appeal submission failed",
                    success=False,
                    error_message=str(e),
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            return ExecutionResult(
                success=False,
                action=ExecutionAction.SUBMIT_APPEAL,
                message=f"Appeal submission failed: {str(e)}",
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

    async def _simulate_appeal_submission(self, appeal: Appeal) -> str:
        """
        Simulate external API call to submit appeal.
        In production, this would call actual payor API.

        Args:
            appeal: Appeal to submit

        Returns:
            External submission reference number
        """
        import asyncio
        import random

        # Simulate network delay
        await asyncio.sleep(0.1)

        # Simulate 95% success rate
        if random.random() < 0.95:
            # Generate mock reference number
            reference = f"APL-{appeal.appeal_id.hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"
            return reference
        else:
            raise Exception("Simulated external API error")

    def check_permission(self, action: ExecutionAction) -> bool:
        """
        Check if current permission level allows action.

        Args:
            action: Action to check

        Returns:
            True if action is allowed
        """
        if self.permission_level == ExecutionPermission.ADMIN:
            return True

        if self.permission_level == ExecutionPermission.WRITE_APPEALS:
            return action in [
                ExecutionAction.SUBMIT_APPEAL,
                ExecutionAction.UPDATE_CLAIM_STATUS,
                ExecutionAction.NOTIFY_STAKEHOLDERS,
            ]

        # READ_ONLY cannot perform any execution actions
        return False

    async def update_claim_status(
        self,
        claim_id: UUID,
        new_status: str,
        updated_by: str,
    ) -> ExecutionResult:
        """
        Update claim status in external system.

        Args:
            claim_id: Claim to update
            new_status: New status value
            updated_by: User performing update

        Returns:
            ExecutionResult with update status
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info("updating_claim_status", claim_id=str(claim_id), new_status=new_status)

        # Check permissions
        if not self.check_permission(ExecutionAction.UPDATE_CLAIM_STATUS):
            error_msg = f"Insufficient permissions: {self.permission_level.value} cannot update claims"

            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id,
                    agent_name="executor_agent",
                    description="Claim update blocked: insufficient permissions",
                    success=False,
                    error_message=error_msg,
                )
            )

            return ExecutionResult(
                success=False,
                action=ExecutionAction.UPDATE_CLAIM_STATUS,
                message=error_msg,
                audit_events=audit_events,
                processing_time_ms=0.0,
            )

        # Audit event for update
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.CLAIM_UPDATED,
                claim_id=claim_id,
                agent_name="executor_agent",
                description=f"Updating claim status to {new_status}",
                metadata={"new_status": new_status, "updated_by": updated_by},
            )
        )

        try:
            # Simulate status update
            import asyncio
            await asyncio.sleep(0.05)

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.CLAIM_UPDATED,
                    claim_id=claim_id,
                    agent_name="executor_agent",
                    description=f"Claim status updated to {new_status}",
                    success=True,
                    metadata={"new_status": new_status},
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            return ExecutionResult(
                success=True,
                action=ExecutionAction.UPDATE_CLAIM_STATUS,
                message=f"Claim status updated to {new_status}",
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            self.logger.error("claim_update_error", claim_id=str(claim_id), error=str(e))

            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id,
                    agent_name="executor_agent",
                    description="Claim update failed",
                    success=False,
                    error_message=str(e),
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            return ExecutionResult(
                success=False,
                action=ExecutionAction.UPDATE_CLAIM_STATUS,
                message=f"Update failed: {str(e)}",
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )
