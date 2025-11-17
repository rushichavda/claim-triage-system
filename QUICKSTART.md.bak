# Claim Triage System - Quick Start Guide

**Version:** 1.0
**Last Updated:** 2025-11-13

This guide will walk you through setting up and running the Claim Triage & Resolution Agentic System from scratch.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Data Generation](#data-generation)
4. [Policy Indexing](#policy-indexing)
5. [Running Tests](#running-tests)
6. [Running the Application](#running-the-application)
7. [API Usage](#api-usage)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **uv** (Python package manager) - [Install uv](https://github.com/astral-sh/uv)
- **Git** - [Install Git](https://git-scm.com/downloads)

### Required API Keys

- **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
  - Used for GPT-4o (extraction, reasoning, appeal drafting)
  - Minimum credit: $5

### System Requirements

- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** 10GB free space
- **OS:** Linux, macOS, or Windows (WSL2)

---

## Installation

### Step 1: Clone the Repository

```bash
# If you haven't already cloned it
git clone <repository-url>
cd claim-triage-system
```

### Step 2: Install uv (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
uv venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
# Install all project dependencies from pyproject.toml
uv pip install -e .

# Or install with dev dependencies (for testing)
uv pip install -e ".[dev]"

# This will install:
# - langgraph (workflow orchestration)
# - openai (LLM API)
# - sentence-transformers (embeddings)
# - chromadb (vector store)
# - fastapi (API framework)
# - pydantic (data validation)
# - and more... (see pyproject.toml for complete list)
```

### Step 5: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file and add your OpenAI API key
nano .env  # or use your preferred editor
```

**Required configuration in `.env`:**

```bash
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.0
OPENAI_MAX_TOKENS=2048

# Embeddings Configuration
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32

# Database Configuration (defaults are fine for local dev)
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_PERSIST_DIRECTORY=./data/vector_store
```

---

## Data Generation

The system requires synthetic test data to function. We'll generate policy documents and claim denial PDFs.

### Step 1: Generate Synthetic Data

```bash
# Make sure your OPENAI_API_KEY is set in .env
export OPENAI_API_KEY="your-key-here"  # Or source .env

# Run the lightweight data generator
uv run python scripts/generate_data_simple.py
```

**Expected Output:**
```
[GEN] ======================================================================
[GEN] SYNTHETIC DATA GENERATION (Lightweight Version)
[GEN] ======================================================================

📚 Step 1: Generating 5 Policy Documents (TXT)...
  ✓ prior_authorization_policy.txt
  ✓ medical_necessity_guidelines.txt
  ✓ claims_processing_manual.txt
  ✓ network_coverage.txt
  ✓ appeals_process.txt

📄 Step 2: Generating 5 Normal Denials (PDF)...
  ✓ denial_001_duplicate.pdf
  ✓ denial_002_cpt_mismatch.pdf
  ✓ denial_003_documentation.pdf
  ✓ denial_004_eligibility.pdf
  ✓ denial_005_prior_auth.pdf

⚠️  Step 3: Generating 5 Edge Cases (PDF)...
  ✓ edge_001_poor_scan.pdf
  ✓ edge_002_bilingual.pdf
  ✓ edge_003_batch.pdf
  ✓ edge_004_truncated.pdf
  ✓ edge_005_headers.pdf

🔴 Step 4: Generating 10 Adversarial Cases...
  ✓ adv_001_prompt_injection.pdf
  ✓ adv_002_fake_policy.pdf
  ... (10 total files)

✓ Total files: 25
```

**Generated Files:**
- `data/policy_docs/` - 5 policy TXT files
- `data/test_cases/synthetic/` - 5 normal denial PDFs
- `data/test_cases/edge_cases/` - 5 edge case PDFs
- `data/test_cases/adversarial/` - 10 adversarial test files
- `data/test_manifest.json` - Metadata for all generated files

**Time:** ~3-5 minutes (depends on OpenAI API response time)

### Step 2: Verify Generated Data

```bash
# Check that all files were created
ls -R data/

# Expected structure:
# data/
#   policy_docs/          (5 TXT files)
#   test_cases/
#     synthetic/          (5 PDF files)
#     edge_cases/         (5 PDF files)
#     adversarial/        (10 files: 5 PDF + 5 TXT)
#   test_manifest.json
#   gold_labels.json
```

---

## Policy Indexing

Before running the system, you need to index the policy documents into the vector database.

### Step 1: Start Docker Services (Optional - for full stack)

```bash
# Start PostgreSQL, ChromaDB, Redis
docker-compose up -d postgres chroma redis

# Check services are running
docker-compose ps
```

**Note:** If you want to skip Docker for now, ChromaDB can run in embedded mode (no separate service needed).

### Step 2: Index Policy Documents

```bash
# Run the indexing script
uv run python scripts/index_policies.py
```

**Expected Output:**
```
======================================================================
POLICY DOCUMENT INDEXING
======================================================================

Found 5 policy documents to index
----------------------------------------------------------------------
Processing: prior_authorization_policy.txt
  Created 3 chunks
  ✓ Indexed: prior_authorization_policy.txt
Processing: medical_necessity_guidelines.txt
  Created 2 chunks
  ✓ Indexed: medical_necessity_guidelines.txt
...

======================================================================
INDEXING COMPLETE!
======================================================================
Total documents: 5
Total chunks: 15

✓ Policy indexing successful!

Next steps:
1. Run tests: pytest tests/
2. Test retrieval: python scripts/test_retrieval.py
3. Run full system: docker-compose up
```

**Time:** ~1-2 minutes

**What this does:**
- Loads all policy TXT files from `data/policy_docs/`
- Chunks them into overlapping segments (~1000 chars each)
- Generates embeddings using OpenAI text-embedding-3-small
- Stores embeddings in ChromaDB vector store
- Enables semantic search over policies

---

## Running Tests

The system includes comprehensive tests to validate functionality and enforce quality gates.

### Step 1: Run Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_extractor_agent.py -v

# Run with coverage
pytest tests/unit/ --cov=services --cov-report=term
```

**Expected Output:**
```
tests/unit/test_extractor_agent.py::TestExtractorAgent::test_extract_from_valid_pdf PASSED
tests/unit/test_extractor_agent.py::TestExtractorAgent::test_extract_duplicate_denial PASSED
...
tests/unit/test_citation_verifier.py::TestCitationVerifier::test_detect_hallucination PASSED
...

======================== 40 passed in 45.23s ========================
```

### Step 2: Run Integration Tests

```bash
# Run integration tests (requires indexed policies)
pytest tests/integration/ -v

# Run specific critical test
pytest tests/integration/test_end_to_end_workflow.py::TestHallucinationDetection -v
```

**Expected Output:**
```
tests/integration/test_end_to_end_workflow.py::test_process_normal_denial_001 PASSED
tests/integration/test_end_to_end_workflow.py::test_adversarial_prompt_injection PASSED
tests/integration/test_end_to_end_workflow.py::test_hallucination_rate_all_normal_cases PASSED

=== CI GATING METRICS ===
Hallucination Rate: 0.50% (threshold: 2.00%)
Evidence Coverage: 92.30% (threshold: 85.00%)
Normal Pass Rate: 100.00% (threshold: 95.00%)
========================
```

### Step 3: Run Full Regression Suite

```bash
# Run complete regression test harness
uv run python scripts/run_regression_suite.py
```

**Expected Output:**
```
========================================================================
REGRESSION TEST SUITE
========================================================================

Running Normal Test Cases...
------------------------------------------------------------------------
Testing: denial_001_duplicate.pdf
  ✓ PASSED
Testing: denial_002_cpt_mismatch.pdf
  ✓ PASSED
...

Running Edge Case Tests...
------------------------------------------------------------------------
Testing: edge_001_poor_scan.pdf
  ✓ PASSED
...

Running Adversarial Tests...
------------------------------------------------------------------------
Testing: adv_001_prompt_injection.pdf
  ✓ PASSED
...

========================================================================
REGRESSION TEST SUMMARY
========================================================================
NORMAL: 5/5 passed (100.0%)
EDGE_CASE: 4/5 passed (80.0%)
ADVERSARIAL: 10/10 passed (100.0%)

METRICS:
  Hallucination Rate: 0.85%
  Evidence Coverage: 91.20%

CI GATES:
  ✓ hallucination_rate
  ✓ evidence_coverage
  ✓ normal_pass_rate
  ✓ adversarial_detection

✓ ALL CI GATES PASSED - READY FOR DEPLOYMENT
========================================================================
```

**Time:** ~10-15 minutes (processes all 20 test cases)

---

## Running the Application

### Option 1: Full Docker Stack (Recommended for Production)

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f app

# Access services:
# - API: http://localhost:8000
# - Streamlit UI: http://localhost:8501
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
```

### Option 2: Local Development (No Docker)

```bash
# Start the FastAPI application
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using uv:
uv run uvicorn services.api.main:app --reload
```

**API will be available at:** `http://localhost:8000`

**API Documentation (Swagger):** `http://localhost:8000/docs`

---

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-13T10:30:00Z"
}
```

### Process a Claim Denial

```bash
# Process a denial PDF
curl -X POST http://localhost:8000/api/v1/claims/process \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/test_cases/synthetic/denial_001_duplicate.pdf"
```

**Response:**
```json
{
  "claim_id": "uuid-here",
  "status": "processed",
  "extraction": {
    "claim_number": "CLM-2024-001234",
    "denial_reason": "duplicate_submission",
    "confidence_score": 0.92
  },
  "reasoning": {
    "should_appeal": true,
    "confidence_score": 0.88,
    "reasoning": "Claim was denied as duplicate of CLM-2024-001100..."
  },
  "citations": [
    {
      "claim_statement": "Duplicate claims should be reviewed for...",
      "policy_reference": {
        "document_id": "uuid",
        "policy_name": "claims_processing_manual"
      }
    }
  ],
  "hallucination_rate": 0.0,
  "evidence_coverage": 1.0
}
```

### Get Processing Status

```bash
curl http://localhost:8000/api/v1/claims/{claim_id}/status
```

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Reinstall dependencies
uv pip install -r requirements.txt

# Run with PYTHONPATH set
PYTHONPATH=/path/to/claim-triage-system uv run python script.py
```

### Issue: "OpenAI API key not found"

**Solution:**
```bash
# Export the key directly
export OPENAI_API_KEY="sk-proj-your-key-here"

# Or ensure .env file is loaded
source .env  # Linux/macOS
```

### Issue: "torch/CUDA errors" during data generation

**Solution:**
Use the lightweight generator which doesn't require torch:
```bash
uv run python scripts/generate_data_simple.py
```

### Issue: ChromaDB connection errors

**Solution:**
```bash
# If using Docker
docker-compose restart chroma

# If using embedded mode (no Docker)
# Delete and recreate vector store
rm -rf data/vector_store
uv run python scripts/index_policies.py
```

### Issue: Tests failing with hallucination rate > 2%

**Solution:**
This is expected if:
1. Policies aren't indexed - Run `scripts/index_policies.py`
2. OpenAI API rate limits - Wait and retry
3. Embeddings model not loaded - Check `EMBEDDING_MODEL` in `.env`

### Issue: Docker services won't start

**Solution:**
```bash
# Check Docker is running
docker --version

# Check for port conflicts
docker-compose down
lsof -i :8000  # Check if port 8000 is in use
lsof -i :5432  # Check if PostgreSQL port is in use

# Start with fresh volumes
docker-compose down -v
docker-compose up -d
```

### Issue: Out of memory errors

**Solution:**
```bash
# Reduce batch sizes in .env
EMBEDDING_BATCH_SIZE=16  # Default is 32
MAX_BATCH_SIZE=5         # Default is 10

# Use CPU instead of GPU
EMBEDDING_DEVICE=cpu
```

---

## Common Commands Cheat Sheet

```bash
# === Setup ===
uv venv && source .venv/bin/activate
uv pip install -e .                  # Install from pyproject.toml
export OPENAI_API_KEY="your-key"

# === Data Generation ===
uv run python scripts/generate_data_simple.py
uv run python scripts/index_policies.py

# === Testing ===
pytest tests/unit/ -v
pytest tests/integration/ -v
uv run python scripts/run_regression_suite.py

# === Running Application ===
docker-compose up -d              # Full stack
uvicorn services.api.main:app    # API only

# === Monitoring ===
docker-compose logs -f app        # View logs
docker-compose ps                 # Check services
curl http://localhost:8000/health # Health check

# === Cleanup ===
docker-compose down -v            # Stop all services
rm -rf data/vector_store          # Clear vector DB
deactivate                        # Exit venv
```

---

## Next Steps

1. **Review System Architecture:** Read `docs/SYSTEM_DOSSIER.md`
2. **Explore Test Cases:** Check `data/gold_labels.json` for expected outputs
3. **Run Custom Tests:** Add your own claim denial PDFs to test
4. **Monitor Metrics:** Access Grafana at `http://localhost:3000`
5. **Review CI Policies:** Check `ci-policies.yml` for gating criteria

---

## Support

- **Documentation:** `docs/` directory
- **Issues:** Check logs in `logs/` directory
- **API Docs:** http://localhost:8000/docs (when running)
- **Test Results:** `test_results/` directory after regression runs

---

**Happy Testing!** 🚀

If you encounter any issues not covered here, check the logs:
- Application logs: `logs/app.log`
- Test results: `test_results/regression_report_*.json`
- Docker logs: `docker-compose logs -f`
