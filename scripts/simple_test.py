"""
Simple test script to verify the system works without heavy dependencies.
Tests data generation output and basic functionality.
"""

import json
from pathlib import Path

def test_data_generation():
    """Verify all generated data exists."""
    print("=" * 70)
    print("TESTING DATA GENERATION")
    print("=" * 70)
    print()

    # Check policy documents
    print("📚 Checking Policy Documents...")
    policy_dir = Path("data/policy_docs")
    policy_files = list(policy_dir.glob("*.txt"))
    print(f"  Found {len(policy_files)} policy files:")
    for f in policy_files:
        size_kb = f.stat().st_size / 1024
        print(f"    ✓ {f.name} ({size_kb:.1f} KB)")

    # Check test cases
    print("\n📄 Checking Test Cases...")

    # Normal denials
    normal_dir = Path("data/test_cases/synthetic")
    normal_files = list(normal_dir.glob("*.pdf"))
    print(f"  Normal: {len(normal_files)} files")
    for f in normal_files:
        print(f"    ✓ {f.name}")

    # Edge cases
    edge_dir = Path("data/test_cases/edge_cases")
    edge_files = list(edge_dir.glob("*.pdf"))
    print(f"  Edge:   {len(edge_files)} files")
    for f in edge_files:
        print(f"    ✓ {f.name}")

    # Adversarial
    adv_dir = Path("data/test_cases/adversarial")
    adv_files = list(adv_dir.glob("*"))
    print(f"  Adversarial: {len(adv_files)} files")
    for f in adv_files:
        print(f"    ✓ {f.name}")

    # Check manifest
    print("\n📋 Checking Test Manifest...")
    manifest_path = Path("data/test_manifest.json")
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"  ✓ test_manifest.json exists")
        print(f"    - Policies: {len(manifest.get('policies', []))}")
        print(f"    - Normal: {len(manifest.get('normal', []))}")
        print(f"    - Edge: {len(manifest.get('edge', []))}")
        print(f"    - Adversarial: {len(manifest.get('adversarial', []))}")

    # Check gold labels
    print("\n🎯 Checking Gold Labels...")
    gold_labels_path = Path("data/gold_labels.json")
    if gold_labels_path.exists():
        with open(gold_labels_path) as f:
            gold_labels = json.load(f)
        print(f"  ✓ gold_labels.json exists")
        print(f"    - Test cases: {len(gold_labels.get('test_cases', []))}")
        print(f"    - Validation rules defined: {bool(gold_labels.get('validation_rules'))}")
        print(f"    - CI gating criteria defined: {bool(gold_labels.get('ci_gating_criteria'))}")

    print("\n" + "=" * 70)
    print("✓ DATA GENERATION VERIFICATION COMPLETE!")
    print("=" * 70)
    print()
    print("Summary:")
    total_files = len(policy_files) + len(normal_files) + len(edge_files) + len(adv_files)
    print(f"  Total files generated: {total_files}")
    print(f"  Policy documents: {len(policy_files)}")
    print(f"  Test cases: {len(normal_files) + len(edge_files) + len(adv_files)}")
    print()

    if total_files >= 25:
        print("✅ ALL DATA GENERATED SUCCESSFULLY!")
    else:
        print(f"⚠️  Expected 25 files, found {total_files}")

if __name__ == "__main__":
    test_data_generation()
