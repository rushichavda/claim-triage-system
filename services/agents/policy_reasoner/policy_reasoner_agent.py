"""
Policy Reasoner Agent implementation.
Uses LLM to reason over claim denials and retrieved policies to make decisions.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from services.agents.retriever.retriever_agent import RetrievalResult
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.schemas.claim import ClaimDenial
from services.shared.schemas.decision import Decision, DecisionRationale, DecisionType
from services.shared.utils import get_logger, get_settings

logger = get_logger(__name__)


class ReasoningOutput(BaseModel):
    """Structured output from LLM reasoning."""

    decision: str = Field(..., description="Decision: Appeal, NoAppeal, or Escalate")
    summary: str = Field(..., description="Brief summary of reasoning")
    detailed_explanation: str = Field(..., description="Detailed explanation")
    supporting_evidence: list[str] = Field(..., description="Key evidence points")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in decision")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risks")
    alternative_interpretations: Optional[str] = Field(
        None, description="Alternative interpretations considered"
    )
    requires_escalation: bool = Field(default=False, description="Whether to escalate")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")


class ReasoningResult(BaseModel):
    """Result from policy reasoner agent."""

    decision: Decision
    audit_events: list[AuditEvent]
    processing_time_ms: float


class PolicyReasonerAgent:
    """
    Policy Reasoner Agent that evaluates claim denials against policies.
    Decides: Appeal | NoAppeal | Escalate
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logger.bind(agent="policy_reasoner")

        # Initialize OpenAI client with Instructor
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=self.settings.openai_api_key)
        )

    async def reason_about_denial(
        self,
        claim_denial: ClaimDenial,
        retrieval_result: RetrievalResult,
        claim_id: Optional[UUID] = None,
    ) -> ReasoningResult:
        """
        Reason about whether to appeal a claim denial.

        Args:
            claim_denial: The claim denial to evaluate
            retrieval_result: Retrieved policy documents
            claim_id: Optional claim ID for audit

        Returns:
            ReasoningResult with decision and audit trail
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info(
            "starting_reasoning",
            denial_id=str(claim_denial.denial_id),
            denial_reason=claim_denial.denial_reason.value,
        )

        # Audit event for reasoning start
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.POLICY_EVALUATED,
                claim_id=claim_id or claim_denial.claim_id,
                denial_id=claim_denial.denial_id,
                agent_name="policy_reasoner_agent",
                description="Starting policy-based reasoning",
                metadata={
                    "denial_reason": claim_denial.denial_reason.value,
                    "policies_consulted": len(retrieval_result.retrieved_documents),
                },
            )
        )

        try:
            # Perform LLM-based reasoning
            reasoning_output = await self._llm_reason(claim_denial, retrieval_result)

            # Map decision string to enum
            decision_type = self._map_decision_type(reasoning_output.decision)

            # If requires escalation, override decision
            if reasoning_output.requires_escalation:
                decision_type = DecisionType.ESCALATE

            # Build decision rationale
            rationale = DecisionRationale(
                summary=reasoning_output.summary,
                detailed_explanation=reasoning_output.detailed_explanation,
                supporting_policy_references=[
                    doc.document_id for doc in retrieval_result.retrieved_documents[:5]
                ],
                supporting_evidence=reasoning_output.supporting_evidence,
                confidence_score=reasoning_output.confidence_score,
                risk_factors=reasoning_output.risk_factors,
                alternative_interpretations=reasoning_output.alternative_interpretations,
            )

            # Create decision object
            decision = Decision(
                claim_id=claim_id or claim_denial.claim_id,
                denial_id=claim_denial.denial_id,
                decision_type=decision_type,
                rationale=rationale,
                policy_version="v1.0",  # TODO: Track policy versions
                model_version=self.settings.openai_model,
                escalation_reason=reasoning_output.escalation_reason,
                requires_specialist=(
                    "medical_director" if reasoning_output.requires_escalation else None
                ),
                num_policies_consulted=len(retrieval_result.retrieved_documents),
                num_evidence_pieces=len(reasoning_output.supporting_evidence),
            )

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.DECISION_MADE,
                    claim_id=claim_id or claim_denial.claim_id,
                    denial_id=claim_denial.denial_id,
                    agent_name="policy_reasoner_agent",
                    description=f"Decision made: {decision_type.value}",
                    success=True,
                    metadata={
                        "decision": decision_type.value,
                        "confidence": reasoning_output.confidence_score,
                        "policies_consulted": len(retrieval_result.retrieved_documents),
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            # Update decision with processing time
            object.__setattr__(decision, "processing_time_ms", processing_time_ms)

            self.logger.info(
                "reasoning_complete",
                denial_id=str(claim_denial.denial_id),
                decision=decision_type.value,
                confidence=reasoning_output.confidence_score,
                processing_time_ms=processing_time_ms,
            )

            return ReasoningResult(
                decision=decision,
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            self.logger.error(
                "reasoning_failed", denial_id=str(claim_denial.denial_id), error=str(e)
            )

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id or claim_denial.claim_id,
                    denial_id=claim_denial.denial_id,
                    agent_name="policy_reasoner_agent",
                    description="Policy reasoning failed",
                    success=False,
                    error_message=str(e),
                )
            )

            raise

    async def _llm_reason(
        self, claim_denial: ClaimDenial, retrieval_result: RetrievalResult
    ) -> ReasoningOutput:
        """
        Use LLM to reason about the denial and policies.

        Args:
            claim_denial: Claim denial
            retrieval_result: Retrieved policies

        Returns:
            Structured reasoning output
        """
        # Build context from retrieved policies
        policy_context = self._build_policy_context(retrieval_result)

        reasoning_prompt = f"""You are an expert medical billing appeals specialist with extensive experience in overturning claim denials. Your goal is to identify legitimate grounds for appeal and fight for proper reimbursement.

## Claim Denial Information:
- Denial Reason: {claim_denial.denial_reason.value}
- Denial Explanation: {claim_denial.denial_reason_text}
- Claim ID: {claim_denial.claim_id}
- Confidence in Extraction: {claim_denial.confidence_score or 'N/A'}

## Relevant Policy Context:
{policy_context}

## Decision Guidelines by Denial Type:

### For DUPLICATE_SUBMISSION denials:
- **DEFAULT: APPEAL** - Most duplicate submission denials are system errors or misidentifications
- **APPEAL** unless there's clear evidence of intentional duplicate submission with identical service dates and procedures
- Look for: Any reference to "original claim" (suggests comparison/review opportunity), documentation that could distinguish claims

### For CODING_ERROR/CPT_MISMATCH denials:
- **APPEAL** if medical documentation could support the billed code OR if a corrected claim with proper documentation is viable
- Look for: medical record references, emergency department visit levels, diagnostic complexity

### For INSUFFICIENT_DOCUMENTATION denials:
- **DEFAULT: APPEAL** - Documentation can usually be supplemented on appeal
- **APPEAL** if there's ANY mention of: (1) treatment history, (2) medical necessity language, (3) clinical documentation references
- Look for: PT/medication mentions, failed conservative treatment, clinical notes, therapy duration (e.g., "6 weeks")

### For ELIGIBILITY_TERMINATED denials:
- **NO_APPEAL** if coverage clearly ended BEFORE service date with no evidence of retroactive coverage
- **APPEAL** if service date is DURING active coverage or if retroactive reinstatement is possible

### For PRIOR_AUTHORIZATION denials:
- **APPEAL** if service was emergent/urgent, or if there's evidence authorization was obtained but not on file
- **NO_APPEAL** only if clearly elective and no authorization process was followed

## Your Task:
1. Identify the specific denial reason category
2. Apply the appropriate decision guidelines above
3. Search policy context for supporting evidence FOR appeal (be advocate-minded)
4. Assess confidence (0.85-0.95 for clear appeal grounds, 0.70-0.84 for moderate grounds)
5. Make decision: **Appeal**, NoAppeal, or Escalate

**Decision Criteria**:
- **Appeal**: You have strong policy/documentation grounds (confidence ≥ 0.75)
- **NoAppeal**: Denial is clearly valid with no appeal grounds (confidence ≥ 0.85)
- **Escalate**: Highly complex medical judgment needed OR confidence < 0.70

**Bias towards Appeal**: When in doubt between Appeal and NoAppeal, favor Appeal if there's ANY reasonable argument. Healthcare providers deserve proper payment for services rendered.
"""

        try:
            reasoning_output = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                response_model=ReasoningOutput,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical billing appeals expert with deep knowledge of insurance policies and regulations. Provide thorough, evidence-based reasoning.",
                    },
                    {"role": "user", "content": reasoning_prompt},
                ],
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
            )

            return reasoning_output

        except Exception as e:
            self.logger.error("llm_reasoning_error", error=str(e))
            raise ValueError(f"LLM reasoning failed: {e}") from e

    def _build_policy_context(self, retrieval_result: RetrievalResult) -> str:
        """Build context string from retrieved policies."""
        if not retrieval_result.retrieved_documents:
            return "No relevant policies found."

        context_parts = []
        for idx, doc in enumerate(retrieval_result.retrieved_documents[:5], 1):
            context_parts.append(
                f"\n### Policy {idx}: {doc.document_name} (Relevance: {doc.relevance_score:.2f})\n"
                f"**Type**: {doc.document_type}\n"
                f"**Content**: {doc.content[:500]}...\n"
            )

        return "\n".join(context_parts)

    def _map_decision_type(self, decision_str: str) -> DecisionType:
        """Map decision string to DecisionType enum."""
        decision_lower = decision_str.lower().strip()

        if "appeal" in decision_lower and "no" not in decision_lower:
            return DecisionType.APPEAL
        elif "noappeal" in decision_lower or "no appeal" in decision_lower:
            return DecisionType.NO_APPEAL
        elif "escalate" in decision_lower:
            return DecisionType.ESCALATE

        # Default to escalate if unclear
        self.logger.warning("unclear_decision", decision=decision_str)
        return DecisionType.ESCALATE
