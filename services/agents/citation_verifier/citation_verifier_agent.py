"""
Citation Verifier Agent implementation.
Verifies that every claim in an appeal has a valid, verifiable source citation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from services.agents.retriever.embedding_service import EmbeddingService
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.schemas.citation import Citation, CitationSpan
from services.shared.utils import get_logger

logger = get_logger(__name__)


class VerificationResult(BaseModel):
    """Result of citation verification."""

    verified_citations: list[Citation]
    failed_citations: list[Citation]
    hallucination_detected: bool
    hallucination_count: int
    total_citations: int
    verification_score: float = Field(..., ge=0.0, le=1.0, description="Overall verification score")
    audit_events: list[AuditEvent]
    processing_time_ms: float


class CitationVerifierAgent:
    """
    Citation Verifier Agent - ensures no hallucinations.
    Verifies every claim statement has a valid source citation with semantic similarity check.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        similarity_threshold: float = 0.7,
    ) -> None:
        self.logger = logger.bind(agent="citation_verifier")
        self.similarity_threshold = similarity_threshold

        # Initialize embedding service for semantic similarity
        self.embedding_service = embedding_service or EmbeddingService()

        self.logger.info(
            "verifier_initialized", similarity_threshold=self.similarity_threshold
        )

    async def verify_citations(
        self,
        citations: list[Citation],
        claim_id: Optional[UUID] = None,
        strict_mode: bool = True,
    ) -> VerificationResult:
        """
        Verify all citations in an appeal.

        Args:
            citations: List of citations to verify
            claim_id: Optional claim ID for audit
            strict_mode: If True, fail on any unverified citation

        Returns:
            VerificationResult with verification status
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info("starting_verification", total_citations=len(citations))

        # Audit event for verification start
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.CITATION_VERIFIED,
                claim_id=claim_id,
                agent_name="citation_verifier_agent",
                description=f"Verifying {len(citations)} citations",
                metadata={"total_citations": len(citations), "strict_mode": strict_mode},
            )
        )

        verified_citations = []
        failed_citations = []

        try:
            # Verify each citation
            for citation in citations:
                is_valid = await self._verify_single_citation(citation)

                if is_valid:
                    # Mark as verified
                    verified_citation = citation.model_copy(
                        update={"verified": True, "verified_at": datetime.utcnow()}
                    )
                    verified_citations.append(verified_citation)
                else:
                    failed_citations.append(citation)

                    # Log hallucination detection
                    self.logger.warning(
                        "citation_verification_failed",
                        claim_text=citation.claim_text[:100],
                        source_text=citation.source_span.extracted_text[:100],
                    )

                    # Audit event for hallucination
                    audit_events.append(
                        AuditEvent(
                            event_type=AuditEventType.HALLUCINATION_DETECTED,
                            claim_id=claim_id,
                            agent_name="citation_verifier_agent",
                            description="Potential hallucination detected",
                            success=False,
                            metadata={
                                "claim_text": citation.claim_text[:200],
                                "source_text": citation.source_span.extracted_text[:200],
                                "verification_score": citation.verification_score or 0.0,
                            },
                        )
                    )

            # Calculate metrics
            total_citations = len(citations)
            hallucination_count = len(failed_citations)
            hallucination_detected = hallucination_count > 0
            verification_score = (
                len(verified_citations) / total_citations if total_citations > 0 else 0.0
            )

            # Final audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.CITATION_VERIFIED,
                    claim_id=claim_id,
                    agent_name="citation_verifier_agent",
                    description=f"Verification complete: {len(verified_citations)}/{total_citations} verified",
                    success=(not strict_mode or not hallucination_detected),
                    metadata={
                        "verified_count": len(verified_citations),
                        "failed_count": hallucination_count,
                        "verification_score": verification_score,
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "verification_complete",
                verified=len(verified_citations),
                failed=hallucination_count,
                score=verification_score,
                processing_time_ms=processing_time_ms,
            )

            result = VerificationResult(
                verified_citations=verified_citations,
                failed_citations=failed_citations,
                hallucination_detected=hallucination_detected,
                hallucination_count=hallucination_count,
                total_citations=total_citations,
                verification_score=verification_score,
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

            # In strict mode, raise error if hallucinations detected
            if strict_mode and hallucination_detected:
                raise ValueError(
                    f"Citation verification failed: {hallucination_count} hallucinations detected"
                )

            return result

        except Exception as e:
            self.logger.error("verification_error", error=str(e))

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    claim_id=claim_id,
                    agent_name="citation_verifier_agent",
                    description="Citation verification failed",
                    success=False,
                    error_message=str(e),
                )
            )

            raise

    async def _verify_single_citation(self, citation: Citation) -> bool:
        """
        Verify a single citation using semantic similarity.

        Args:
            citation: Citation to verify

        Returns:
            True if citation is valid
        """
        try:
            # Get claim text and source text
            claim_text = citation.claim_text.strip()
            source_text = citation.source_span.extracted_text.strip()

            # Check if source text is empty
            if not source_text or len(source_text) < 10:
                self.logger.warning("empty_source_text", claim_text=claim_text[:100])
                return False

            # Compute semantic similarity using embeddings
            claim_embedding = self.embedding_service.embed_query(claim_text)
            source_embedding = self.embedding_service.embed_document(source_text)

            similarity = self.embedding_service.compute_similarity(
                claim_embedding, source_embedding
            )

            # Update citation with verification score
            object.__setattr__(citation, "verification_score", similarity)

            # Check if similarity meets threshold
            is_valid = similarity >= self.similarity_threshold

            self.logger.debug(
                "citation_verified",
                similarity=similarity,
                threshold=self.similarity_threshold,
                is_valid=is_valid,
            )

            return is_valid

        except Exception as e:
            self.logger.error(
                "single_citation_verification_error",
                claim_text=citation.claim_text[:100],
                error=str(e),
            )
            return False

    def create_citation_from_text(
        self,
        claim_text: str,
        source_span: CitationSpan,
        citation_type: str = "evidence",
    ) -> Citation:
        """
        Create a citation object from claim text and source span.

        Args:
            claim_text: The claim statement
            source_span: Source span with document reference
            citation_type: Type of citation

        Returns:
            Citation object
        """
        return Citation(
            claim_text=claim_text,
            source_span=source_span,
            verified=False,
            citation_type=citation_type,
        )

    def calculate_citation_coverage(
        self, total_claims: int, verified_citations: int
    ) -> float:
        """
        Calculate citation coverage percentage.

        Args:
            total_claims: Total number of claims in appeal
            verified_citations: Number of verified citations

        Returns:
            Coverage percentage (0.0 to 1.0)
        """
        if total_claims == 0:
            return 0.0

        return min(1.0, verified_citations / total_claims)
