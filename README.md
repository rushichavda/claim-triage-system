# 🏥 Claim Triage & Resolution Agentic System

**Production-grade multi-agent system for healthcare claim denial triage and automated appeal generation**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-stateful-green.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Overview

**🎯 Status: ALL ASSIGNMENT DELIVERABLES COMPLETE**

This system implements a **production-grade multi-agent orchestration workflow** that:
- ✅ Ingests claim denial PDFs with byte-level offset tracking
- ✅ Extracts structured data with confidence scoring
- ✅ Retrieves relevant policies using **OpenAI text-embedding-3-small** (1536-dim embeddings)
- ✅ Reasons over policies to decide: **Appeal | NoAppeal | Escalate**
- ✅ Generates appeals with **verifiable citations** (hallucination prevention)
- ✅ Provides human-in-the-loop review interface
- ✅ Executes with guarded permissions and full audit trail

**Assignment Deliverables:**
- ✅ **System Dossier** (2 pages) - Complete architecture, agent taxonomy, threat model
- ✅ **Monitoring & Postmortem Playbook** (1 page) - KPIs, alerts, incident runbooks
- ✅ **Model Card & Documentation** (1 page) - Capabilities, limitations, ethical considerations
- ✅ **Business Case & 90-Day Rollout Plan** (1 page) - ROI model, KPI improvements, milestones
- ✅ **Prototype Repo** - Runnable Docker stack with 6 specialized agents
- ✅ **20+ Test Cases** - 10 synthetic + 10 adversarial with gold labels
- ✅ **CI/CD Harness** - Regression suite with hallucination gating
- ✅ **Zero-Hallucination Enforcement** - <2% rate via Citation Verifier

### 🎯 Key Features

- **Zero-Hallucination Tolerance**: Every claim must link to verifiable source (doc ID + byte offsets)
- **HIPAA-Ready**: Encryption-at-rest, tokenized PHI in logs, redaction mechanics
- **Production-Grade**: Stateful agents, CI/CD gating, adversarial robustness testing
- **Observable**: Full audit trail, LangSmith tracing, Prometheus metrics

---

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────┐
│  Ingest Service │ ─── PDF Parser (byte-level offsets)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extractor Agent │ ─── LLM + Instructor (structured output)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Retriever Agent │ ─── OpenAI Embeddings + ChromaDB
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Policy Reasoner     │ ─── LLM-based reasoning
│ (Appeal/NoAppeal/   │
│  Escalate)          │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Appeal Drafter      │ ─── Generates appeals with citations
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Citation Verifier   │ ─── Semantic similarity check
│ (Hallucination Det.)│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Human Review UI     │ ─── Streamlit (Approve/Reject/Modify)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Execution Adapter   │ ─── Writeback with permissions
└─────────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| **Orchestration** | LangGraph (stateful multi-agent workflow) |
| **LLM** | OpenAI GPT-4o (reasoning, extraction, drafting) |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Vector Store** | ChromaDB (embedded, no separate service) |
| **Database** | PostgreSQL + pgvector (ACID audit logs) |
| **Caching** | Redis (state management, rate limiting) |
| **API** | FastAPI (async, type-safe) |
| **UI** | Streamlit (human review interface) |
| **Observability** | LangSmith + Prometheus + Grafana |
| **Security** | Fernet encryption, Presidio (PHI redaction) |

---

## 🚀 Quick Start

Choose your setup based on your needs:
- **Development Mode** - Lightweight, no Docker, for testing and development
- **Production Mode** - Full stack with Docker, monitoring, and all services

---

### 📦 Development Mode (Recommended for Testing)

Perfect for: Local development, testing, debugging

**What's included:** Core agents, ChromaDB (embedded), no Docker needed

#### Step 1: Prerequisites

```bash
# Required
- Python 3.11+
- OpenAI API key
```

#### Step 2: Setup Environment

```bash
# Clone and navigate to directory
cd claim-triage-system

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

#### Step 3: Generate Test Data

```bash
# Set your API key
export OPENAI_API_KEY="sk-proj-your-key-here"

# Generate 25 test files (5 policies + 20 test cases)
python scripts/generate_data_simple.py
```

**Output:** `data/policy_docs/` and `data/test_cases/` populated with test files

#### Step 4: Index Policies

```bash
# Index policy documents into ChromaDB (embedded mode)
python scripts/index_policies_openai.py
```

**Output:** ChromaDB vector store created at `data/vector_store/`

#### Step 5: Run Tests

```bash
# Run unit tests
pytest tests/unit/ -v

# Run regression suite (validates all 20 test cases)
python scripts/run_regression_suite.py
```

**Expected:** Hallucination rate <2%, Evidence coverage >85%

#### Step 6: Test Single Claim

```bash
# Process a single claim denial
python scripts/test_single_claim.py
```

**That's it!** You now have a working development environment.

**What you DON'T need in dev mode:**
- ❌ Docker / Docker Compose
- ❌ PostgreSQL database
- ❌ Redis cache
- ❌ Streamlit UI
- ❌ Prometheus / Grafana monitoring

---

### 🐳 Production Mode (Full Stack)

Perfect for: Production deployment, demos, full feature testing

**What's included:** All services, monitoring, UI, databases

#### Step 1: Prerequisites

```bash
# Required
- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- 8GB RAM minimum (16GB recommended)
```

#### Step 2: Setup Environment

```bash
# Clone and navigate to directory
cd claim-triage-system

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

#### Step 3: Generate Test Data

```bash
# Set your API key
export OPENAI_API_KEY="sk-proj-your-key-here"

# Generate test data
python scripts/generate_data_simple.py
```

#### Step 4: Index Policies

```bash
# Create virtual environment (for indexing script)
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Index policies
python scripts/index_policies_openai.py
```

#### Step 5: Start Docker Stack

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f app
```

**Services started:**
- ✅ FastAPI (port 8000) - REST API
- ✅ PostgreSQL (port 5432) - Database
- ✅ ChromaDB (port 8001) - Vector store
- ✅ Redis (port 6379) - Cache
- ✅ Streamlit (port 8501) - UI
- ✅ Prometheus (port 9090) - Metrics
- ✅ Grafana (port 3000) - Dashboards

#### Step 6: Access Services

- **API Documentation**: http://localhost:8000/docs
- **Human Review UI**: http://localhost:8501
- **Metrics Dashboard**: http://localhost:3000 (login: admin/admin)
- **Prometheus**: http://localhost:9090

#### Step 7: Run Demo

```bash
# Process sample claims through full workflow
./run_demo.sh --docker
```

**That's it!** Full production stack is running.

---

### 🧪 Quick Validation

After setup, verify everything works:

```bash
# Health check
curl http://localhost:8000/health

# Process a test claim
curl -X POST http://localhost:8000/api/v1/claims/process \
  -F "file=@data/test_cases/synthetic/denial_001_duplicate.pdf"

# Check metrics
curl http://localhost:9090/metrics | grep hallucination_rate
```

---

## 📚 Additional Resources

- **System Architecture**: [`docs/SYSTEM_DOSSIER.md`](docs/SYSTEM_DOSSIER.md)
- **Citation System Deep-Dive**: [`docs/CITATION_DEEP_DIVE.md`](docs/CITATION_DEEP_DIVE.md)
- **Monitoring & Alerts**: [`docs/MONITORING_PLAYBOOK.md`](docs/MONITORING_PLAYBOOK.md)
- **Model Card**: [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)
- **Business Case**: [`docs/BUSINESS_CASE.md`](docs/BUSINESS_CASE.md)
- **Embedding Usage**: [`docs/EMBEDDING_USAGE.md`](docs/EMBEDDING_USAGE.md)

---

## 🧪 Testing

### Test Structure

```
tests/
├── unit/              # Unit tests for individual agents
├── integration/       # Integration tests (multi-agent flows)
├── adversarial/       # Red-team adversarial test cases
└── regression/        # Regression harness (20 testcases)
```

### Run Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Adversarial tests
make test-adversarial
```

### CI Gating

```yaml
# CI policy: Block merge if:
- hallucination_rate > 2%
- evidence_coverage < 85%
- test_pass_rate < 100%
```

---

## 📊 Data Schemas

### Core Models

- **Claim & ClaimDenial**: Structured claim data with PHI fields (encrypted)
- **Citation & CitationSpan**: Byte-level source tracking
- **AuditEvent & AuditLog**: Immutable audit trail
- **Decision & DecisionRationale**: Policy reasoning output
- **Appeal & AppealDraft**: Generated appeals with citations

### Example: Citation with Byte Offsets

```json
{
  "citation_id": "cit-123",
  "claim_text": "Policy Section 4.2.1 states...",
  "source_span": {
    "document_id": "doc-456",
    "start_byte": 1234,
    "end_byte": 1450,
    "extracted_text": "Emergency services exception...",
    "page_number": 3,
    "extraction_confidence": 0.95
  },
  "verified": true,
  "verification_score": 0.92
}
```

---

## 🔐 Security & Compliance

### HIPAA Controls

- ✅ **Encryption-at-Rest**: Fernet (AES-256) for PHI fields
- ✅ **Tokenized Logging**: PHI replaced with deterministic tokens
- ✅ **Redaction**: Presidio-based PII/PHI detection
- ✅ **Least Privilege**: Guarded execution permissions (READ_ONLY | WRITE_APPEALS | ADMIN)
- ✅ **Audit Trail**: Immutable append-only logs with full lineage

### Threat Model

| Risk | Severity | Mitigation | Detection |
|------|----------|------------|-----------|
| Hallucination | **CRITICAL** | Citation verification, semantic similarity | Audit events, CI gating |
| PHI Leak | **CRITICAL** | Encryption, tokenization, redaction | Structured logging, alerts |
| Prompt Injection | HIGH | Input validation, sandboxing | Adversarial tests |
| Data Poisoning | HIGH | Document hash verification | Content integrity checks |

---

## 📈 Monitoring & Observability

### Key Metrics (Prometheus)

```python
# Hallucination rate (CRITICAL)
hallucination_rate = failed_citations / total_citations

# Evidence coverage
evidence_coverage = verified_citations / total_claims

# False accept rate
false_accept_rate = incorrect_approvals / total_decisions

# Cost per case
cost_per_case = total_tokens * token_cost
```

### Alerts

- 🚨 **Hallucination rate > 2%**: Block deployments, escalate to humans
- ⚠️ **Evidence coverage < 85%**: Review appeal quality
- ⚠️ **Avg latency > 30s**: Scale infrastructure

---

## 🛠️ Development

### Project Structure

```
claim-triage-system/
├── services/
│   ├── agents/           # All agent implementations
│   │   ├── extractor/
│   │   ├── retriever/
│   │   ├── policy_reasoner/
│   │   ├── citation_verifier/
│   │   ├── appeal_drafter/
│   │   └── executor/
│   ├── ingest/           # PDF parsing
│   ├── orchestrator/     # LangGraph workflow
│   ├── human_review/     # Streamlit UI
│   └── shared/           # Schemas, utilities
├── data/
│   ├── policy_docs/      # Policy document store
│   ├── test_cases/       # 20 test cases (10 synthetic + 10 adversarial)
│   └── vector_store/     # ChromaDB persistence
├── tests/
├── docs/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### Add a New Agent

1. Create directory: `services/agents/your_agent/`
2. Implement: `your_agent_agent.py` with clear API contract
3. Add to workflow: Update `services/orchestrator/workflow.py`
4. Write tests: `tests/unit/test_your_agent.py`
5. Update docs

---

## 📖 Documentation

### Core Documentation (Assignment Deliverables)

1. **System Dossier** (2 pages): [`docs/SYSTEM_DOSSIER.md`](docs/SYSTEM_DOSSIER.md)
   - Complete architecture diagrams and service maps
   - Agent taxonomy with detailed specifications
   - Data contracts and schemas
   - Threat model & risk management framework
   - HIPAA compliance controls

2. **Monitoring & Postmortem Playbook** (1 page): [`docs/MONITORING_PLAYBOOK.md`](docs/MONITORING_PLAYBOOK.md)
   - Key metrics (KPIs) and alert thresholds
   - Canary deployment & rollback procedures
   - Incident runbook for hallucination events
   - Grafana dashboard configuration

3. **Model Card & Documentation** (1 page): [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)
   - Training/prompt provenance
   - Model capabilities and limitations
   - Recommended usage and required human checks
   - Ethical considerations and bias mitigation

4. **Business Case & 90-Day Rollout Plan** (1 page): [`docs/BUSINESS_CASE.md`](docs/BUSINESS_CASE.md)
   - Expected ROI model (638% 3-year ROI)
   - Measurable KPI improvements
   - Detailed 90-day rollout milestones
   - Risk mitigation and staffing changes

### Additional Documentation

- **Setup Comparison**: [`SETUP_COMPARISON.md`](SETUP_COMPARISON.md) - Development vs Production mode comparison
- **Project Completion Summary**: [`PROJECT_COMPLETION_SUMMARY.md`](PROJECT_COMPLETION_SUMMARY.md)
- **Implementation Status**: [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md)
- **Model Configuration**: [`docs/MODEL_CONFIGURATION.md`](docs/MODEL_CONFIGURATION.md)
- **Running Guide**: [`docs/RUNNING_GUIDE.md`](docs/RUNNING_GUIDE.md)

---

## 🤝 Contributing

```bash
# Setup pre-commit hooks
pre-commit install

# Run full CI pipeline locally
make all

# Format code before commit
make format
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- **LangGraph**: Stateful multi-agent orchestration
- **OpenAI**: GPT-4o for reasoning and text-embedding-3-small for embeddings

---

## 📞 Support

- **Issues**: https://github.com/your-org/claim-triage-system/issues
- **Docs**: https://docs.your-org.com/claim-triage

---

**Built with ❤️ for healthcare compliance automation**
