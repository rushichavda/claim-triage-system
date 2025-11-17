"""
Decision-making schemas for policy reasoner agent.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class DecisionType(str, Enum):
    """Possible decision outcomes from policy reasoner."""

    APPEAL = "appeal"  # Automated appeal should be filed
    NO_APPEAL = "no_appeal"  # Denial is valid, do not appeal
    ESCALATE = "escalate"  # Requires human judgment


class DecisionRationale(BaseModel):
    """Structured reasoning for a decision."""

    model_config = ConfigDict(frozen=True)

    # Primary reasoning
    summary: str = Field(..., description="Brief summary of decision reasoning")
    detailed_explanation: str = Field(..., description="Detailed explanation of decision logic")

    # Supporting factors
    supporting_policy_references: list[UUID] = Field(
        default_factory=list, description="Policy document IDs supporting decision"
    )
    supporting_evidence: list[str] = Field(
        default_factory=list, description="Key evidence points"
    )

    # Risk assessment
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in decision correctness"
    )
    risk_factors: list[str] = Field(
        default_factory=list, description="Identified risk factors"
    )

    # Alternative considerations
    alternative_interpretations: Optional[str] = Field(
        None, description="Other possible interpretations considered"
    )


class Decision(BaseModel):
    """
    Final decision from policy reasoner agent.
    Determines whether to appeal, not appeal, or escalate.
    """

    decision_id: UUID = Field(default_factory=uuid4, description="Unique decision identifier")
    claim_id: UUID = Field(..., description="Reference to claim")
    denial_id: UUID = Field(..., description="Reference to denial")

    # Decision
    decision_type: DecisionType = Field(..., description="The decision made")
    rationale: DecisionRationale = Field(..., description="Structured reasoning")

    # Context
    policy_version: str = Field(..., description="Version of policy used")
    model_version: str = Field(..., description="Model version used for reasoning")

    # Metadata
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    decided_by: str = Field(default="policy_reasoner_agent", description="Agent name")

    # Escalation details
    escalation_reason: Optional[str] = Field(
        None, description="Why escalation is needed (if ESCALATE)"
    )
    requires_specialist: Optional[str] = Field(
        None, description="Type of specialist needed (if ESCALATE)"
    )

    # Quality metrics
    processing_time_ms: Optional[float] = Field(None, description="Processing time in ms")
    num_policies_consulted: int = Field(default=0, description="Number of policies reviewed")
    num_evidence_pieces: int = Field(default=0, description="Number of evidence pieces reviewed")
