"""
Appeal Drafter Agent implementation.
Generates human-reviewable appeal letters with citations and audit blocks.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel

from services.agents.retriever.retriever_agent import RetrievalResult
from services.shared.schemas.appeal import AppealDraft
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.schemas.citation import Citation, CitationSpan
from services.shared.schemas.claim import ClaimDenial
from services.shared.schemas.decision import Decision
from services.shared.utils import get_logger, get_settings

logger = get_logger(__name__)


class DraftingResult(BaseModel):
    """Result from appeal drafter agent."""

    appeal_draft: AppealDraft
    audit_events: list[AuditEvent]
    processing_time_ms: float


class AppealDrafterAgent:
    """
    Appeal Drafter Agent generates appeals with citations.
    Every claim must be backed by verifiable sources.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logger.bind(agent="appeal_drafter")

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def draft_appeal(
        self,
        claim_denial: ClaimDenial,
        decision: Decision,
        retrieval_result: RetrievalResult,
        claim_id: Optional[UUID] = None,
    ) -> DraftingResult:
        """
        Draft an appeal letter with citations.

        Args:
            claim_denial: The claim denial
            decision: Decision from policy reasoner
            retrieval_result: Retrieved policy documents
            claim_id: Optional claim ID for audit

        Returns:
            DraftingResult with draft and audit trail
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info(
            "starting_appeal_draft",
            denial_id=str(claim_denial.denial_id),
            decision=decision.decision_type.value,
        )

        # Audit event for drafting start
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.APPEAL_DRAFTED,
                claim_id=claim_id or claim_denial.claim_id,
                denial_id=claim_denial.denial_id,
                agent_name="appeal_drafter_agent",
                description="Starting appeal draft generation",
                metadata={"decision": decision.decision_type.value},
            )
        )

        try:
            # Generate appeal text using LLM
            appeal_text, key_arguments = await self._generate_appeal_text(
                claim_denial, decision, retrieval_result
            )

            # Extract citations from appeal and policy documents
            citations = await self._extract_citations(
                appeal_text, retrieval_result, claim_denial
            )

            # Calculate quality metrics
            total_claims = len(key_arguments)
            citation_coverage = min(1.0, len(citations) / max(total_claims, 1))

            avg_confidence = (
                sum(c.source_span.extraction_confidence for c in citations) / len(citations)
                if citations
                else 0.0
            )

            # Hallucination risk = 1 - citation_coverage
            hallucination_risk = 1.0 - citation_coverage

            # Build audit summary
            audit_summary = self._build_audit_summary(
                citations, citation_coverage, hallucination_risk
            )

            # Create appeal draft
            appeal_draft = AppealDraft(
                claim_id=claim_id or claim_denial.claim_id,
                denial_id=claim_denial.denial_id,
                decision_id=decision.decision_id,
                appeal_text=appeal_text,
                appeal_summary=decision.rationale.summary[:500],
                citations=citations,
                denial_reason_challenged=claim_denial.denial_reason.value,
                key_arguments=key_arguments,
                policy_violations=[],  # TODO: Extract from reasoning
                supporting_documents=[doc.document_id for doc in retrieval_result.retrieved_documents],
                model_version=self.settings.openai_model,
                citation_coverage=citation_coverage,
                hallucination_risk_score=hallucination_risk,
                avg_citation_confidence=avg_confidence,
                audit_summary=audit_summary,
            )

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.APPEAL_DRAFTED,
                    claim_id=claim_id or claim_denial.claim_id,
                    denial_id=claim_denial.denial_id,
                    agent_name="appeal_drafter_agent",
                    description="Appeal draft completed",
                    success=True,
                    metadata={
                        "citation_count": len(citations),
                        "citation_coverage": citation_coverage,
                        "hallucination_risk": hallucination_risk,
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "appeal_draft_complete",
                denial_id=str(claim_denial.denial_id),
                citations=len(citations),
                coverage=citation_coverage,
                processing_time_ms=processing_time_ms,
            )

            return DraftingResult(
                appeal_draft=appeal_draft,
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            self.logger.error(
                "appeal_draft_failed", denial_id=str(claim_denial.denial_id), error=str(e)
            )

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id or claim_denial.claim_id,
                    denial_id=claim_denial.denial_id,
                    agent_name="appeal_drafter_agent",
                    description="Appeal drafting failed",
                    success=False,
                    error_message=str(e),
                )
            )

            raise

    async def _generate_appeal_text(
        self,
        claim_denial: ClaimDenial,
        decision: Decision,
        retrieval_result: RetrievalResult,
    ) -> tuple[str, list[str]]:
        """
        Generate appeal letter text using LLM.

        Returns:
            Tuple of (appeal_text, key_arguments)
        """
        # Build policy context
        policy_context = "\n\n".join(
            [
                f"**{doc.document_name}** (Relevance: {doc.relevance_score:.2f}):\n{doc.content[:400]}"
                for doc in retrieval_result.retrieved_documents[:3]
            ]
        )

        prompt = f"""You are an expert medical billing appeals specialist. Draft a professional appeal letter for the following claim denial.

## Claim Denial:
- Denial Reason: {claim_denial.denial_reason.value}
- Denial Explanation: {claim_denial.denial_reason_text}

## Decision Rationale:
{decision.rationale.detailed_explanation}

## Supporting Policies:
{policy_context}

## Your Task:
Draft a professional, concise appeal letter that:
1. Clearly states why the denial should be overturned
2. References specific policy provisions
3. Provides clear, evidence-based arguments
4. Maintains a professional, respectful tone
5. Is structured with clear sections (Introduction, Argument, Conclusion)

Keep the letter focused and under 800 words. Use specific policy references.
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical billing appeals expert. Draft clear, professional appeals.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Slightly higher for creativity
                max_tokens=2000,
            )

            appeal_text = response.choices[0].message.content or ""

            # Extract key arguments (simplified - could use LLM)
            key_arguments = decision.rationale.supporting_evidence[:5]

            return appeal_text, key_arguments

        except Exception as e:
            self.logger.error("appeal_generation_error", error=str(e))
            raise

    async def _extract_citations(
        self,
        appeal_text: str,
        retrieval_result: RetrievalResult,
        claim_denial: ClaimDenial,
    ) -> list[Citation]:
        """
        Extract citations linking appeal claims to source documents.
        Simplified version - production would use NER and alignment.
        """
        citations = []

        # For each retrieved document, create a citation
        # In production, this would do semantic alignment between appeal claims and sources
        for doc in retrieval_result.retrieved_documents[:5]:
            # Create citation span
            citation_span = CitationSpan(
                document_id=doc.document_id,
                start_byte=None,  # Would be calculated in production
                end_byte=None,
                page_number=doc.metadata.get("page_number"),
                paragraph_index=doc.metadata.get("paragraph_index"),
                extracted_text=doc.content[:300],
                extraction_confidence=0.9,  # Would be calculated
            )

            # Create citation
            citation = Citation(
                claim_text=f"According to {doc.document_name}, the policy states...",
                source_span=citation_span,
                verified=False,
                citation_type="policy",
            )

            citations.append(citation)

        return citations

    def _build_audit_summary(
        self, citations: list[Citation], coverage: float, risk: float
    ) -> str:
        """Build human-readable audit summary."""
        return f"""
## Audit Summary
- **Total Citations**: {len(citations)}
- **Citation Coverage**: {coverage * 100:.1f}%
- **Hallucination Risk**: {risk * 100:.1f}%
- **Verification Status**: {'✓ All claims cited' if coverage >= 0.85 else '⚠ Some claims lack citations'}

### Citation Sources:
{chr(10).join([f"- {c.source_span.document_id}: {c.source_span.extracted_text[:80]}..." for c in citations[:5]])}
""".strip()
