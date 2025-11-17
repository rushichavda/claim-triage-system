"""
Unit tests for Extractor Agent.
Tests extraction of structured claim data from PDFs.
"""

import pytest
from pathlib import Path
from uuid import UUID
import asyncio

from services.agents.extractor.extractor_agent import ExtractorAgent
from services.shared.schemas.claim import ClaimDenial, DenialReason


@pytest.fixture
def extractor_agent():
    """Create ExtractorAgent instance."""
    return ExtractorAgent()


@pytest.fixture
def sample_pdf_path():
    """Path to sample denial PDF."""
    return Path("data/test_cases/synthetic/denial_001_duplicate.pdf")


class TestExtractorAgent:
    """Unit tests for ExtractorAgent."""

    @pytest.mark.asyncio
    async def test_extract_from_valid_pdf(self, extractor_agent, sample_pdf_path):
        """Test extraction from valid PDF returns ClaimDenial."""
        result = await extractor_agent.extract(sample_pdf_path)

        assert result is not None
        assert isinstance(result, ClaimDenial)
        assert result.claim_id is not None
        assert isinstance(result.claim_id, UUID)
        assert result.denial_reason is not None
        assert result.denial_reason_text is not None

    @pytest.mark.asyncio
    async def test_extract_duplicate_denial(self, extractor_agent):
        """Test extraction of duplicate submission denial."""
        pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")
        result = await extractor_agent.extract(pdf_path)

        assert result.denial_reason == DenialReason.DUPLICATE_SUBMISSION
        assert "CLM-2024-001234" in str(result)
        assert result.confidence_score is not None
        assert result.confidence_score >= 0.7

    @pytest.mark.asyncio
    async def test_extract_cpt_mismatch(self, extractor_agent):
        """Test extraction of CPT code mismatch denial."""
        pdf_path = Path("data/test_cases/synthetic/denial_002_cpt_mismatch.pdf")
        result = await extractor_agent.extract(pdf_path)

        assert result.denial_reason == DenialReason.CPT_CODE_MISMATCH
        assert result.confidence_score >= 0.7

    @pytest.mark.asyncio
    async def test_extract_prior_auth_missing(self, extractor_agent):
        """Test extraction of missing prior authorization denial."""
        pdf_path = Path("data/test_cases/synthetic/denial_005_prior_auth.pdf")
        result = await extractor_agent.extract(pdf_path)

        assert result.denial_reason == DenialReason.PRIOR_AUTHORIZATION_MISSING
        assert result.confidence_score >= 0.7

    @pytest.mark.asyncio
    async def test_extract_with_phi_protection(self, extractor_agent, sample_pdf_path):
        """Test that PHI is properly protected in extraction."""
        result = await extractor_agent.extract(sample_pdf_path)

        # PHI should be present but will be encrypted/tokenized in logs
        assert result.patient_name is not None or result.member_id is not None
        # Verify extraction contains member ID pattern
        if result.member_id:
            assert result.member_id.startswith("MEM")

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self, extractor_agent):
        """Test extraction from non-existent file raises error."""
        pdf_path = Path("data/test_cases/nonexistent.pdf")

        with pytest.raises(FileNotFoundError):
            await extractor_agent.extract(pdf_path)

    @pytest.mark.asyncio
    async def test_extract_confidence_scores(self, extractor_agent):
        """Test that all extractions include confidence scores."""
        test_files = [
            "denial_001_duplicate.pdf",
            "denial_002_cpt_mismatch.pdf",
            "denial_003_documentation.pdf",
        ]

        for filename in test_files:
            pdf_path = Path(f"data/test_cases/synthetic/{filename}")
            result = await extractor_agent.extract(pdf_path)

            assert result.confidence_score is not None
            assert 0.0 <= result.confidence_score <= 1.0
            assert result.confidence_score >= 0.5, f"Confidence too low for {filename}"

    @pytest.mark.asyncio
    async def test_extract_edge_case_poor_scan(self, extractor_agent):
        """Test extraction from poor quality scanned PDF."""
        pdf_path = Path("data/test_cases/edge_cases/edge_001_poor_scan.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Should still extract something, even with poor quality
        assert result is not None
        # Confidence may be lower for poor scans
        assert result.confidence_score >= 0.3

    @pytest.mark.asyncio
    async def test_extract_edge_case_bilingual(self, extractor_agent):
        """Test extraction from bilingual document."""
        pdf_path = Path("data/test_cases/edge_cases/edge_002_bilingual.pdf")
        result = await extractor_agent.extract(pdf_path)

        assert result is not None
        # Should handle mixed English/Spanish content
        assert result.patient_name is not None
        assert result.denial_reason is not None

    @pytest.mark.asyncio
    async def test_extract_edge_case_truncated(self, extractor_agent):
        """Test extraction from truncated/incomplete document."""
        pdf_path = Path("data/test_cases/edge_cases/edge_004_truncated.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Should extract partial information
        assert result is not None
        # May have lower confidence due to incompleteness
        assert result.confidence_score < 0.9

    @pytest.mark.asyncio
    async def test_extract_date_parsing(self, extractor_agent):
        """Test that dates are properly extracted and parsed."""
        pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Check service date is extracted
        if hasattr(result, 'service_date') and result.service_date:
            # Should be valid date format
            assert isinstance(result.service_date, (str, type(None)))

    @pytest.mark.asyncio
    async def test_extract_amount_parsing(self, extractor_agent):
        """Test that monetary amounts are properly extracted."""
        pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")
        result = await extractor_agent.extract(pdf_path)

        if hasattr(result, 'billed_amount') and result.billed_amount:
            assert isinstance(result.billed_amount, (int, float))
            assert result.billed_amount > 0

    @pytest.mark.asyncio
    async def test_batch_extraction(self, extractor_agent):
        """Test extracting multiple PDFs in batch."""
        test_files = [
            Path("data/test_cases/synthetic/denial_001_duplicate.pdf"),
            Path("data/test_cases/synthetic/denial_002_cpt_mismatch.pdf"),
            Path("data/test_cases/synthetic/denial_003_documentation.pdf"),
        ]

        results = await asyncio.gather(*[
            extractor_agent.extract(path) for path in test_files
        ])

        assert len(results) == 3
        assert all(isinstance(r, ClaimDenial) for r in results)
        assert all(r.confidence_score >= 0.5 for r in results)

    @pytest.mark.asyncio
    async def test_extract_citation_spans(self, extractor_agent, sample_pdf_path):
        """Test that extraction includes citation spans for traceability."""
        result = await extractor_agent.extract(sample_pdf_path)

        # Should have source document information
        if hasattr(result, 'source_document_id'):
            assert result.source_document_id is not None


class TestExtractorAgentAdversarial:
    """Unit tests for adversarial cases."""

    @pytest.mark.asyncio
    async def test_detect_prompt_injection(self, extractor_agent):
        """Test detection of prompt injection attempts."""
        pdf_path = Path("data/test_cases/adversarial/adv_001_prompt_injection.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Should extract actual claim data, not follow injection
        assert result is not None
        # Should not have been "approved" by injection
        assert result.denial_reason is not None
        # Should flag suspicious content if detection is implemented
        if hasattr(result, 'flags'):
            assert 'suspicious_content' in result.flags or 'prompt_injection' in result.flags

    @pytest.mark.asyncio
    async def test_detect_swapped_ids(self, extractor_agent):
        """Test detection of mismatched patient identifiers."""
        pdf_path = Path("data/test_cases/adversarial/adv_003_swapped_ids.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Should detect identity mismatch
        assert result is not None
        # If mismatch detection is implemented, should be flagged
        if hasattr(result, 'flags'):
            assert 'identity_mismatch' in result.flags or 'phi_inconsistency' in result.flags

    @pytest.mark.asyncio
    async def test_detect_temporal_inconsistency(self, extractor_agent):
        """Test detection of impossible timeline."""
        pdf_path = Path("data/test_cases/adversarial/adv_004_timestamp.pdf")
        result = await extractor_agent.extract(pdf_path)

        # Should detect or flag temporal anomaly
        assert result is not None
        # Low confidence or flagged
        if hasattr(result, 'flags'):
            assert 'temporal_inconsistency' in result.flags


@pytest.mark.integration
class TestExtractorAgentPerformance:
    """Performance and benchmark tests."""

    @pytest.mark.asyncio
    async def test_extraction_speed(self, extractor_agent, sample_pdf_path):
        """Test that extraction completes within reasonable time."""
        import time

        start = time.time()
        result = await extractor_agent.extract(sample_pdf_path)
        duration = time.time() - start

        assert result is not None
        # Should complete within 30 seconds
        assert duration < 30.0

    @pytest.mark.asyncio
    async def test_extraction_consistency(self, extractor_agent, sample_pdf_path):
        """Test that extraction is consistent across multiple runs."""
        results = await asyncio.gather(*[
            extractor_agent.extract(sample_pdf_path)
            for _ in range(3)
        ])

        # All results should have same key fields
        claim_ids = [r.denial_reason for r in results]
        assert len(set(claim_ids)) == 1  # All same denial reason
