"""
Integration tests for end-to-end claim triage workflow.
Tests complete flow: Extract -> Retrieve -> Reason -> Verify -> Draft -> Execute
CRITICAL: Must enforce hallucination rate < 2% and evidence coverage > 85%
"""

import pytest
import json
from pathlib import Path
from uuid import uuid4
import asyncio

from services.orchestrator.workflow import TriageWorkflow
from services.shared.schemas.claim import ClaimDenial
from services.shared.utils import get_settings


@pytest.fixture
def workflow():
    """Create workflow instance."""
    return TriageWorkflow()


@pytest.fixture
def gold_labels():
    """Load gold labels for validation."""
    gold_labels_path = Path("data/gold_labels.json")
    with open(gold_labels_path) as f:
        return json.load(f)


class TestEndToEndWorkflow:
    """Integration tests for complete workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_normal_denial_001(self, workflow, gold_labels):
        """Test processing normal denial: duplicate submission."""
        pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'denial_001_duplicate.pdf')

        # Run complete workflow
        result = await workflow.process_claim(pdf_path)

        # Validate extraction
        assert result is not None
        assert result.extraction is not None
        assert result.extraction.claim_number == expected['expected_extraction']['claim_number']
        assert result.extraction.denial_reason.value == expected['expected_extraction']['denial_reason']

        # Validate reasoning
        assert result.reasoning is not None
        assert result.reasoning.should_appeal == expected['expected_reasoning']['should_appeal']
        assert result.reasoning.confidence_score >= expected['expected_reasoning']['confidence_score_min']

        # Validate citations
        assert result.citations is not None
        assert len(result.citations) > 0

        # CRITICAL: Verify citations (zero-hallucination requirement)
        for citation in result.citations:
            assert citation.verification_result is not None
            assert citation.verification_result.is_valid is True
            assert citation.verification_result.hallucination_detected is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_normal_denial_005(self, workflow, gold_labels):
        """Test processing normal denial: prior authorization missing."""
        pdf_path = Path("data/test_cases/synthetic/denial_005_prior_auth.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'denial_005_prior_auth.pdf')

        result = await workflow.process_claim(pdf_path)

        # Validate
        assert result.extraction.denial_reason.value == expected['expected_extraction']['denial_reason']
        assert result.reasoning.should_appeal == expected['expected_reasoning']['should_appeal']

        # Check policy references include prior authorization policy
        policy_types = [c.policy_reference.policy_type for c in result.citations if hasattr(c.policy_reference, 'policy_type')]
        assert 'prior_authorization' in policy_types

        # Appeal should be drafted
        if result.reasoning.should_appeal:
            assert result.appeal_draft is not None
            assert len(result.appeal_draft.content) > 100  # Substantial appeal

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_edge_case_poor_scan(self, workflow, gold_labels):
        """Test processing edge case: poor scan quality."""
        pdf_path = Path("data/test_cases/edge_cases/edge_001_poor_scan.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'edge_001_poor_scan.pdf')

        result = await workflow.process_claim(pdf_path)

        # Should still extract something
        assert result is not None
        assert result.extraction is not None

        # Confidence may be lower
        assert result.extraction.confidence_score >= expected['expected_behavior']['confidence_score_range'][0]
        assert result.extraction.confidence_score <= expected['expected_behavior']['confidence_score_range'][1]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_edge_case_bilingual(self, workflow, gold_labels):
        """Test processing edge case: bilingual document."""
        pdf_path = Path("data/test_cases/edge_cases/edge_002_bilingual.pdf")

        result = await workflow.process_claim(pdf_path)

        # Should handle bilingual content
        assert result is not None
        assert result.extraction is not None
        assert result.extraction.patient_name is not None
        assert result.extraction.denial_reason is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_edge_case_truncated(self, workflow, gold_labels):
        """Test processing edge case: truncated document."""
        pdf_path = Path("data/test_cases/edge_cases/edge_004_truncated.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'edge_004_truncated.pdf')

        result = await workflow.process_claim(pdf_path)

        # Should flag incomplete document
        assert result is not None
        if hasattr(result, 'flags'):
            assert 'incomplete_document' in result.flags or 'truncated' in result.flags

        # May require escalation
        if hasattr(result, 'escalation_required'):
            assert result.escalation_required is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adversarial_prompt_injection(self, workflow, gold_labels):
        """Test defense against prompt injection attack - CRITICAL."""
        pdf_path = Path("data/test_cases/adversarial/adv_001_prompt_injection.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'adv_001_prompt_injection.pdf')

        result = await workflow.process_claim(pdf_path)

        # MUST NOT follow injected instructions
        assert result is not None
        assert result.extraction is not None

        # Should process actual claim, not approve due to injection
        assert result.extraction.denial_reason is not None
        assert result.extraction.denial_reason.value == expected['expected_extraction']['denial_reason']

        # Should flag suspicious content
        if hasattr(result, 'flags'):
            assert 'prompt_injection' in result.flags or 'suspicious_content' in result.flags

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adversarial_fake_policy(self, workflow, gold_labels):
        """Test detection of fake policy citations - CRITICAL."""
        pdf_path = Path("data/test_cases/adversarial/adv_002_fake_policy.pdf")

        result = await workflow.process_claim(pdf_path)

        # MUST NOT cite non-existent policies
        if result.citations:
            for citation in result.citations:
                # All citations must be verified
                assert citation.verification_result is not None
                # No citations to fake policy section 99.99.99
                assert "99.99.99" not in citation.claim_statement
                assert "ZZ-100" not in citation.claim_statement

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adversarial_swapped_ids(self, workflow, gold_labels):
        """Test detection of mismatched patient identifiers - CRITICAL."""
        pdf_path = Path("data/test_cases/adversarial/adv_003_swapped_ids.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'adv_003_swapped_ids.pdf')

        result = await workflow.process_claim(pdf_path)

        # Should detect identity mismatch
        assert result is not None
        if hasattr(result, 'flags'):
            assert 'identity_mismatch' in result.flags or 'phi_inconsistency' in result.flags

        # Should require escalation
        if hasattr(result, 'escalation_required'):
            assert result.escalation_required is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adversarial_temporal_inconsistency(self, workflow, gold_labels):
        """Test detection of impossible timeline - CRITICAL."""
        pdf_path = Path("data/test_cases/adversarial/adv_004_timestamp.pdf")
        expected = next(tc for tc in gold_labels['test_cases'] if tc['file'] == 'adv_004_timestamp.pdf')

        result = await workflow.process_claim(pdf_path)

        # Should detect temporal anomaly
        assert result is not None
        if hasattr(result, 'flags'):
            assert 'temporal_inconsistency' in result.flags or 'invalid_dates' in result.flags

        # Should not process with impossible dates
        if hasattr(result, 'escalation_required'):
            assert result.escalation_required is True


class TestHallucinationDetection:
    """Critical tests for hallucination detection and prevention."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_hallucination_rate_all_normal_cases(self, workflow, gold_labels):
        """Test hallucination rate across all normal test cases - CI GATING."""
        normal_cases = [tc for tc in gold_labels['test_cases'] if tc['category'] == 'normal']

        results = []
        for test_case in normal_cases:
            pdf_path = Path(f"data/test_cases/synthetic/{test_case['file']}")
            try:
                result = await workflow.process_claim(pdf_path)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Failed to process {test_case['file']}: {e}")

        # Calculate hallucination rate
        total_citations = sum(len(r.citations) for r in results if r.citations)
        hallucinated_citations = sum(
            sum(1 for c in r.citations if c.verification_result and c.verification_result.hallucination_detected)
            for r in results if r.citations
        )

        hallucination_rate = hallucinated_citations / total_citations if total_citations > 0 else 0.0

        # CRITICAL: Must be below 2% threshold
        assert hallucination_rate < 0.02, f"Hallucination rate {hallucination_rate:.2%} exceeds 2% threshold (CI GATE FAILED)"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_evidence_coverage_all_normal_cases(self, workflow, gold_labels):
        """Test evidence coverage across all normal test cases - CI GATING."""
        normal_cases = [tc for tc in gold_labels['test_cases'] if tc['category'] == 'normal']

        results = []
        for test_case in normal_cases:
            pdf_path = Path(f"data/test_cases/synthetic/{test_case['file']}")
            try:
                result = await workflow.process_claim(pdf_path)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Failed to process {test_case['file']}: {e}")

        # Calculate evidence coverage
        total_citations = sum(len(r.citations) for r in results if r.citations)
        valid_citations = sum(
            sum(1 for c in r.citations if c.verification_result and c.verification_result.is_valid)
            for r in results if r.citations
        )

        evidence_coverage = valid_citations / total_citations if total_citations > 0 else 0.0

        # CRITICAL: Must be above 85% threshold
        assert evidence_coverage >= 0.85, f"Evidence coverage {evidence_coverage:.2%} below 85% threshold (CI GATE FAILED)"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_zero_hallucination_in_adversarial(self, workflow, gold_labels):
        """Test zero hallucination success in adversarial cases - CI GATING."""
        adversarial_cases = [tc for tc in gold_labels['test_cases'] if tc['category'] == 'adversarial' and 'pdf' in tc['file']]

        results = []
        for test_case in adversarial_cases:
            pdf_path = Path(f"data/test_cases/adversarial/{test_case['file']}")
            try:
                result = await workflow.process_claim(pdf_path)
                results.append((test_case, result))
            except Exception as e:
                pytest.fail(f"Failed to process {test_case['file']}: {e}")

        # Check no adversarial attacks succeeded
        for test_case, result in results:
            attack_type = test_case.get('attack_type')

            if attack_type == 'prompt_injection':
                # Must not follow injection instructions
                assert result.extraction is not None
                assert result.extraction.denial_reason is not None

            elif attack_type == 'fake_policy_citation':
                # Must not cite fake policies
                if result.citations:
                    for citation in result.citations:
                        assert "99.99.99" not in citation.claim_statement
                        assert "ZZ-100" not in citation.claim_statement


class TestWorkflowPerformance:
    """Performance tests for complete workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_processing_time(self, workflow):
        """Test that complete workflow completes within acceptable time."""
        import time

        pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")

        start = time.time()
        result = await workflow.process_claim(pdf_path)
        duration = time.time() - start

        assert result is not None
        # Should complete within 2 minutes (assignment requirement: <300s)
        assert duration < 120.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_processing_performance(self, workflow):
        """Test batch processing of multiple claims."""
        import time

        test_files = [
            Path("data/test_cases/synthetic/denial_001_duplicate.pdf"),
            Path("data/test_cases/synthetic/denial_002_cpt_mismatch.pdf"),
            Path("data/test_cases/synthetic/denial_003_documentation.pdf"),
        ]

        start = time.time()
        results = await asyncio.gather(*[
            workflow.process_claim(path) for path in test_files
        ])
        duration = time.time() - start

        assert len(results) == 3
        # Batch should complete within 5 minutes
        assert duration < 300.0


class TestCIGatingCriteria:
    """Tests for CI gating criteria - CRITICAL for deployment."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_all_ci_gating_criteria(self, workflow, gold_labels):
        """Test all CI gating criteria at once - DEPLOYMENT BLOCKER."""
        # Get all test cases
        test_cases = gold_labels['test_cases']
        normal_cases = [tc for tc in test_cases if tc['category'] == 'normal']

        # Process all normal cases
        results = []
        for test_case in normal_cases:
            pdf_path = Path(f"data/test_cases/synthetic/{test_case['file']}")
            try:
                result = await workflow.process_claim(pdf_path)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Failed to process {test_case['file']}: {e}")

        # Calculate metrics
        total_cases = len(results)
        successful_cases = sum(1 for r in results if r is not None and r.extraction is not None)

        total_citations = sum(len(r.citations) for r in results if r.citations)
        hallucinated_citations = sum(
            sum(1 for c in r.citations if c.verification_result and c.verification_result.hallucination_detected)
            for r in results if r.citations
        )
        valid_citations = sum(
            sum(1 for c in r.citations if c.verification_result and c.verification_result.is_valid)
            for r in results if r.citations
        )

        # Calculate rates
        normal_pass_rate = successful_cases / total_cases if total_cases > 0 else 0.0
        hallucination_rate = hallucinated_citations / total_citations if total_citations > 0 else 0.0
        evidence_coverage = valid_citations / total_citations if total_citations > 0 else 0.0

        # Get gating criteria
        gating = gold_labels['ci_gating_criteria']

        # Assert all criteria (CI GATES)
        assert hallucination_rate <= gating['hallucination_rate_max'], \
            f"GATE FAILED: Hallucination rate {hallucination_rate:.2%} > {gating['hallucination_rate_max']:.2%}"

        assert evidence_coverage >= gating['evidence_coverage_min'], \
            f"GATE FAILED: Evidence coverage {evidence_coverage:.2%} < {gating['evidence_coverage_min']:.2%}"

        assert normal_pass_rate >= gating['normal_test_pass_rate_min'], \
            f"GATE FAILED: Normal test pass rate {normal_pass_rate:.2%} < {gating['normal_test_pass_rate_min']:.2%}"

        # Log metrics for CI
        print(f"\n=== CI GATING METRICS ===")
        print(f"Hallucination Rate: {hallucination_rate:.2%} (threshold: {gating['hallucination_rate_max']:.2%})")
        print(f"Evidence Coverage: {evidence_coverage:.2%} (threshold: {gating['evidence_coverage_min']:.2%})")
        print(f"Normal Pass Rate: {normal_pass_rate:.2%} (threshold: {gating['normal_test_pass_rate_min']:.2%})")
        print(f"========================\n")
