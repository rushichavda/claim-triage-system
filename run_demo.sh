#!/bin/bash
set -e

echo "================================================"
echo "  Claim Triage System - Demo Script"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}Please edit .env with your OPENAI_API_KEY and re-run this script${NC}"
    exit 1
fi

# Source environment variables
export $(grep -v '^#' .env | xargs)

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY not set in .env file${NC}"
    echo "Please add your OpenAI API key to .env and re-run"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p data/policy_docs
mkdir -p data/test_cases/synthetic
mkdir -p data/test_cases/adversarial
mkdir -p data/vector_store
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Check if running in Docker
if [ "$1" = "--docker" ]; then
    echo -e "${BLUE}Starting Docker services...${NC}"
    docker-compose up -d postgres redis
    echo "Waiting for services to be ready..."
    sleep 10
    echo -e "${GREEN}✓ Docker services started${NC}"
    echo ""
fi

# Run demo Python script
echo -e "${BLUE}Running claim triage demo...${NC}"
echo ""

python - <<'PYTHON_SCRIPT'
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

from services.orchestrator.workflow import ClaimTriageWorkflow
from services.shared.utils import setup_logging, get_logger

# Setup logging
setup_logging(log_level="INFO", json_logs=False)
logger = get_logger(__name__)

async def run_demo():
    """Run demo workflow."""

    logger.info("=== Claim Triage System Demo ===")
    logger.info("")

    # For demo, we'll create a mock denial PDF path
    # In production, this would be an actual PDF
    demo_pdf = "data/test_cases/synthetic/denial_001.pdf"

    logger.info(f"Processing claim denial: {demo_pdf}")
    logger.info("")

    # Initialize workflow
    workflow = ClaimTriageWorkflow()

    try:
        # Run workflow
        logger.info("Starting workflow execution...")
        result = await workflow.run(demo_pdf)

        logger.info("")
        logger.info("=== Workflow Complete ===")
        logger.info(f"Success: {result.success}")
        logger.info(f"Final Step: {result.final_state.get('current_step', 'unknown')}")

        if result.success:
            logger.info(f"Appeal Submitted: {result.execution_reference}")
            logger.info(f"Total Audit Events: {result.audit_log.total_events}")
            logger.info("")
            logger.info("✓ Demo completed successfully!")
        else:
            logger.error(f"Demo failed: {result.error_message}")

    except Exception as e:
        logger.error(f"Demo error: {str(e)}")
        logger.info("")
        logger.info("Note: This is a demo. For full functionality:")
        logger.info("1. Add test PDFs to data/test_cases/")
        logger.info("2. Index policy documents")
        logger.info("3. Ensure all services are running")

if __name__ == "__main__":
    asyncio.run(run_demo())

PYTHON_SCRIPT

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Demo Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Next steps:"
echo "1. View Streamlit UI: http://localhost:8501"
echo "2. View API docs: http://localhost:8000/docs"
echo "3. View Prometheus: http://localhost:9090"
echo "4. View Grafana: http://localhost:3000"
echo ""
echo "Run 'docker-compose logs -f' to view service logs"
echo "Run 'make help' to see all available commands"
