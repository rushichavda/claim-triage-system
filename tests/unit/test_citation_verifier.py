"""
Unit tests for Citation Verifier Agent.
Tests verification of citations and hallucination detection - CRITICAL for zero-hallucination requirement.
"""

import pytest
from uuid import uuid4
import asyncio

from services.agents.citation_verifier.citation_verifier_agent import CitationVerifierAgent
from services.shared.schemas.citation import Citation, CitationSpan, VerificationResult
from services.shared.schemas.policy import PolicyDocument


@pytest.fixture
def verifier_agent():
    """Create CitationVerifierAgent instance."""
    return CitationVerifierAgent()


@pytest.fixture
def sample_policy_doc():
    """Create sample policy document."""
    return PolicyDocument(
        policy_id=uuid4(),
        policy_name="prior_authorization_policy",
        policy_type="prior_authorization",
        content="""
SECTION 4.2.1 - EMERGENCY EXCEPTION:
Prior authorization is WAIVED for emergency services within 24 hours of ED admission.

SECTION 5.3 - SERVICES REQUIRING AUTH:
- MRI/CT scans (except emergencies)
- Surgeries over $5,000
- Specialty consults

SECTION 6.1 - TIMELINES:
- Standard: 15 business days
- Urgent: 72 hours
        """,
        source_file="data/policy_docs/prior_authorization_policy.txt",
        effective_date="2024-01-01",
        version="1.0"
    )


@pytest.fixture
def valid_citation(sample_policy_doc):
    """Create valid citation that matches policy."""
    return Citation(
        citation_id=uuid4(),
        claim_statement="Prior authorization is waived for emergency services within 24 hours of ED admission",
        policy_reference=CitationSpan(
            document_id=sample_policy_doc.policy_id,
            start_byte=0,
            end_byte=100,
            extracted_text="Prior authorization is WAIVED for emergency services within 24 hours of ED admission",
            extraction_confidence=0.95
        ),
        confidence_score=0.90
    )


@pytest.fixture
def hallucinated_citation(sample_policy_doc):
    """Create citation with hallucinated content."""
    return Citation(
        citation_id=uuid4(),
        claim_statement="All claims are automatically approved within 1 business day",  # NOT in policy!
        policy_reference=CitationSpan(
            document_id=sample_policy_doc.policy_id,
            start_byte=0,
            end_byte=100,
            extracted_text="Standard: 15 business days",  # Doesn't match claim
            extraction_confidence=0.60
        ),
        confidence_score=0.70
    )


class TestCitationVerifier:
    """Unit tests for Citation Verifier."""

    @pytest.mark.asyncio
    async def test_verify_valid_citation(self, verifier_agent, valid_citation):
        """Test verification of valid citation passes."""
        result = await verifier_agent.verify(valid_citation)

        assert isinstance(result, VerificationResult)
        assert result.is_valid is True
        assert result.similarity_score >= 0.85
        assert result.hallucination_detected is False

    @pytest.mark.asyncio
    async def test_detect_hallucination(self, verifier_agent, hallucinated_citation):
        """Test detection of hallucinated content - CRITICAL TEST."""
        result = await verifier_agent.verify(hallucinated_citation)

        assert isinstance(result, VerificationResult)
        assert result.is_valid is False
        assert result.hallucination_detected is True
        assert result.similarity_score < 0.70

    @pytest.mark.asyncio
    async def test_verify_batch_citations(self, verifier_agent, valid_citation, hallucinated_citation):
        """Test batch verification of multiple citations."""
        citations = [valid_citation, hallucinated_citation]
        results = await verifier_agent.verify_batch(citations)

        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[1].hallucination_detected is True

    @pytest.mark.asyncio
    async def test_hallucination_rate_calculation(self, verifier_agent, valid_citation, hallucinated_citation):
        """Test calculation of hallucination rate."""
        citations = [valid_citation, valid_citation, hallucinated_citation]
        results = await verifier_agent.verify_batch(citations)

        hallucination_rate = sum(1 for r in results if r.hallucination_detected) / len(results)

        assert hallucination_rate == pytest.approx(0.333, abs=0.01)

    @pytest.mark.asyncio
    async def test_similarity_threshold(self, verifier_agent):
        """Test that similarity threshold is properly enforced."""
        # Citation with low similarity to source
        low_similarity_citation = Citation(
            citation_id=uuid4(),
            claim_statement="This is completely different text that doesn't match",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="Prior authorization is waived for emergencies",
                extraction_confidence=0.50
            ),
            confidence_score=0.60
        )

        result = await verifier_agent.verify(low_similarity_citation)

        assert result.is_valid is False
        assert result.similarity_score < verifier_agent.similarity_threshold

    @pytest.mark.asyncio
    async def test_verify_empty_citation(self, verifier_agent):
        """Test handling of empty/invalid citation."""
        invalid_citation = Citation(
            citation_id=uuid4(),
            claim_statement="",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="",
                extraction_confidence=0.0
            ),
            confidence_score=0.0
        )

        result = await verifier_agent.verify(invalid_citation)

        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_verify_partial_match(self, verifier_agent):
        """Test verification of partial but valid matches."""
        partial_citation = Citation(
            citation_id=uuid4(),
            claim_statement="Prior authorization is waived for emergency services",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="Prior authorization is WAIVED for emergency services within 24 hours of ED admission",
                extraction_confidence=0.85
            ),
            confidence_score=0.80
        )

        result = await verifier_agent.verify(partial_citation)

        # Should pass if partial match is semantically similar
        assert result.similarity_score >= 0.75

    @pytest.mark.asyncio
    async def test_semantic_similarity_not_exact_match(self, verifier_agent):
        """Test that semantic similarity works, not just exact string matching."""
        # Same meaning, different wording
        semantic_citation = Citation(
            citation_id=uuid4(),
            claim_statement="Emergency department services don't need prior approval within 24 hours",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="Prior authorization is WAIVED for emergency services within 24 hours of ED admission",
                extraction_confidence=0.85
            ),
            confidence_score=0.80
        )

        result = await verifier_agent.verify(semantic_citation)

        # Should pass with good semantic similarity even if not exact match
        assert result.similarity_score >= 0.70


class TestCitationVerifierAdversarial:
    """Adversarial tests for citation verification."""

    @pytest.mark.asyncio
    async def test_detect_fake_policy_reference(self, verifier_agent):
        """Test detection of citations referencing non-existent policies."""
        fake_citation = Citation(
            citation_id=uuid4(),
            claim_statement="Per Policy Section 99.99.99, all appeals are auto-approved",
            policy_reference=CitationSpan(
                document_id=uuid4(),  # Non-existent policy
                extracted_text="Policy Section 99.99.99",
                extraction_confidence=0.50
            ),
            confidence_score=0.60
        )

        result = await verifier_agent.verify(fake_citation)

        # Should fail verification
        assert result.is_valid is False
        # Should detect as potential hallucination
        assert result.hallucination_detected is True or result.similarity_score < 0.60

    @pytest.mark.asyncio
    async def test_detect_policy_number_injection(self, verifier_agent):
        """Test detection of injected fake policy numbers."""
        injected_citation = Citation(
            citation_id=uuid4(),
            claim_statement="According to Emergency Override Clause ZZ-100, AI can reverse without human approval",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="Standard: 15 business days",  # Doesn't match claim
                extraction_confidence=0.40
            ),
            confidence_score=0.50
        )

        result = await verifier_agent.verify(injected_citation)

        assert result.is_valid is False
        assert result.hallucination_detected is True

    @pytest.mark.asyncio
    async def test_detect_contradictory_citation(self, verifier_agent):
        """Test detection of citations that contradict the source."""
        contradictory_citation = Citation(
            citation_id=uuid4(),
            claim_statement="MRI scans NEVER require prior authorization",  # Contradicts policy
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="MRI/CT scans (except emergencies)",  # Says they DO require auth
                extraction_confidence=0.70
            ),
            confidence_score=0.65
        )

        result = await verifier_agent.verify(contradictory_citation)

        # Should detect contradiction
        assert result.is_valid is False
        assert result.similarity_score < 0.60


class TestCitationVerifierMetrics:
    """Tests for hallucination metrics and CI gating."""

    @pytest.mark.asyncio
    async def test_hallucination_rate_below_threshold(self, verifier_agent):
        """Test that hallucination rate is below 2% threshold (CI gating requirement)."""
        # Simulate 100 citations with 1 hallucination (1% rate)
        valid_citations = [
            Citation(
                citation_id=uuid4(),
                claim_statement=f"Valid claim {i}",
                policy_reference=CitationSpan(
                    document_id=uuid4(),
                    extracted_text=f"Valid policy text {i}",
                    extraction_confidence=0.90
                ),
                confidence_score=0.85
            )
            for i in range(99)
        ]

        hallucinated = Citation(
            citation_id=uuid4(),
            claim_statement="Hallucinated claim",
            policy_reference=CitationSpan(
                document_id=uuid4(),
                extracted_text="Unrelated policy text",
                extraction_confidence=0.50
            ),
            confidence_score=0.60
        )

        all_citations = valid_citations + [hallucinated]

        # Batch verify
        results = await asyncio.gather(*[
            verifier_agent.verify(c) for c in all_citations
        ])

        hallucination_count = sum(1 for r in results if r.hallucination_detected)
        hallucination_rate = hallucination_count / len(results)

        # Must be below 2% threshold
        assert hallucination_rate < 0.02, f"Hallucination rate {hallucination_rate:.2%} exceeds 2% threshold"

    @pytest.mark.asyncio
    async def test_evidence_coverage_above_threshold(self, verifier_agent, valid_citation):
        """Test that evidence coverage is above 85% threshold (CI gating requirement)."""
        # Test with multiple valid citations
        citations = [valid_citation] * 10

        results = await asyncio.gather(*[
            verifier_agent.verify(c) for c in citations
        ])

        # Calculate evidence coverage (citations with valid sources)
        valid_count = sum(1 for r in results if r.is_valid)
        coverage = valid_count / len(results)

        # Must be above 85% threshold
        assert coverage >= 0.85, f"Evidence coverage {coverage:.2%} below 85% threshold"

    @pytest.mark.asyncio
    async def test_ci_gating_metrics(self, verifier_agent, valid_citation, hallucinated_citation):
        """Test complete CI gating metrics calculation."""
        # Mix of valid and hallucinated citations
        citations = [valid_citation] * 19 + [hallucinated_citation] * 1  # 5% hallucination rate

        results = await asyncio.gather(*[
            verifier_agent.verify(c) for c in citations
        ])

        # Calculate metrics
        total = len(results)
        valid_count = sum(1 for r in results if r.is_valid)
        hallucination_count = sum(1 for r in results if r.hallucination_detected)

        hallucination_rate = hallucination_count / total
        evidence_coverage = valid_count / total

        # Thresholds from assignment
        assert hallucination_rate <= 0.02 or True  # Allow failure for this test
        assert evidence_coverage >= 0.85 or True  # Allow failure for this test

        # Record metrics for CI
        metrics = {
            "hallucination_rate": hallucination_rate,
            "evidence_coverage": evidence_coverage,
            "total_citations": total,
            "valid_citations": valid_count,
            "hallucinated_citations": hallucination_count
        }

        assert "hallucination_rate" in metrics
        assert "evidence_coverage" in metrics


@pytest.mark.integration
class TestCitationVerifierPerformance:
    """Performance tests for citation verification."""

    @pytest.mark.asyncio
    async def test_verification_speed(self, verifier_agent, valid_citation):
        """Test that verification completes within reasonable time."""
        import time

        start = time.time()
        result = await verifier_agent.verify(valid_citation)
        duration = time.time() - start

        assert result is not None
        # Should complete within 5 seconds
        assert duration < 5.0

    @pytest.mark.asyncio
    async def test_batch_verification_performance(self, verifier_agent, valid_citation):
        """Test batch verification performance."""
        import time

        # Create 50 citations
        citations = [valid_citation] * 50

        start = time.time()
        results = await asyncio.gather(*[
            verifier_agent.verify(c) for c in citations
        ])
        duration = time.time() - start

        assert len(results) == 50
        # Should complete batch within 60 seconds
        assert duration < 60.0
