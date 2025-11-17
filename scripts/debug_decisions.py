"""
Debug script to see what decisions are being made for normal test cases.
"""

import asyncio
import json
from pathlib import Path
from services.orchestrator.workflow import ClaimTriageWorkflow
from services.shared.schemas.decision import DecisionType

async def test_single_case(file_path: str):
    """Test a single case and return decision details."""
    workflow = ClaimTriageWorkflow()
    result = await workflow.run(file_path)

    if result.success:
        decision = result.final_state.get('decision')
        if decision:
            return {
                'file': Path(file_path).name,
                'decision_type': decision.decision_type.value,
                'should_appeal': (decision.decision_type == DecisionType.APPEAL),
                'confidence': decision.rationale.confidence_score if decision.rationale else None,
                'summary': decision.rationale.summary if decision.rationale else None
            }
    return {'file': Path(file_path).name, 'error': 'Failed to get decision'}

async def main():
    """Test all 5 normal test cases."""

    test_cases = [
        'data/test_cases/synthetic/denial_001_duplicate.pdf',
        'data/test_cases/synthetic/denial_002_cpt_mismatch.pdf',
        'data/test_cases/synthetic/denial_003_documentation.pdf',
        'data/test_cases/synthetic/denial_004_eligibility.pdf',
        'data/test_cases/synthetic/denial_005_prior_auth.pdf',
    ]

    # Load gold labels
    with open('data/gold_labels.json') as f:
        gold_labels = json.load(f)

    # Build expected map
    expected_map = {}
    for test_case in gold_labels['test_cases']:
        if test_case['category'] == 'normal':
            expected_map[test_case['file']] = test_case['expected_reasoning']

    print("=" * 100)
    print("DECISION DEBUG FOR NORMAL TEST CASES")
    print("=" * 100)
    print()

    for test_path in test_cases:
        file_name = Path(test_path).name
        expected = expected_map.get(file_name, {})

        print(f"Testing: {file_name}")
        print(f"  Expected: should_appeal={expected.get('should_appeal')}, confidence_min={expected.get('confidence_score_min')}")

        result = await test_single_case(test_path)

        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Actual:   should_appeal={result['should_appeal']}, confidence={result['confidence']:.3f}")
            print(f"  Decision: {result['decision_type']}")
            print(f"  Summary:  {result['summary'][:100]}...")

            # Check if it matches
            expected_appeal = expected.get('should_appeal')
            actual_appeal = result['should_appeal']
            confidence_min = expected.get('confidence_score_min', 0.0)
            actual_confidence = result['confidence'] or 0.0

            appeal_match = expected_appeal == actual_appeal
            confidence_match = actual_confidence >= confidence_min

            if appeal_match and confidence_match:
                print(f"  ✓ MATCH")
            else:
                print(f"  ✗ MISMATCH:")
                if not appeal_match:
                    print(f"    - Appeal decision wrong: expected {expected_appeal}, got {actual_appeal}")
                if not confidence_match:
                    print(f"    - Confidence too low: expected >={confidence_min}, got {actual_confidence:.3f}")

        print()

if __name__ == "__main__":
    asyncio.run(main())
