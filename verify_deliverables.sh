#!/bin/bash

echo "================================================"
echo "  Deliverables Verification Script"
echo "================================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        count=$(find "$1" -type f | wc -l)
        echo -e "${GREEN}✓${NC} $1 ($count files)"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

echo "Core Documentation:"
check_file "docs/SYSTEM_DOSSIER.md"
check_file "docs/MONITORING_PLAYBOOK.md"
check_file "docs/MODEL_CARD.md"
check_file "docs/BUSINESS_CASE.md"
echo ""

echo "Additional Documentation:"
check_file "README.md"
check_file "QUICKSTART.md"
check_file "PROJECT_COMPLETION_SUMMARY.md"
check_file "DELIVERABLES_CHECKLIST.md"
echo ""

echo "Infrastructure:"
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file "ci-policies.yml"
check_file "run_demo.sh"
check_file "pyproject.toml"
check_file ".gitignore"
echo ""

echo "Core Services:"
check_dir "services/agents/extractor"
check_dir "services/agents/retriever"
check_dir "services/agents/policy_reasoner"
check_dir "services/agents/citation_verifier"
check_dir "services/agents/appeal_drafter"
check_dir "services/agents/executor"
check_dir "services/orchestrator"
check_dir "services/ingest"
echo ""

echo "Test Cases:"
check_dir "data/test_cases/synthetic"
check_dir "data/test_cases/adversarial"
check_dir "data/policy_docs"
echo ""

echo "Tests:"
check_file "tests/unit/test_extractor_agent.py"
check_file "tests/unit/test_citation_verifier.py"
check_file "tests/unit/test_retriever_agent.py"
check_file "tests/integration/test_end_to_end_workflow.py"
echo ""

echo "Scripts:"
check_file "scripts/run_regression_suite.py"
check_file "scripts/generate_data_simple.py"
check_file "scripts/index_policies.py"
echo ""

echo "================================================"
echo "  Verification Complete!"
echo "================================================"
