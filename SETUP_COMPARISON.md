# Setup Comparison: Development vs Production

Quick reference guide for choosing between development and production setup.

---

## Quick Decision Matrix

| Your Goal | Recommended Setup |
|-----------|------------------|
| Testing the system locally | **Development Mode** |
| Running unit/regression tests | **Development Mode** |
| Debugging agent logic | **Development Mode** |
| Learning how the system works | **Development Mode** |
| Demoing to stakeholders | **Production Mode** |
| Deploying to staging/production | **Production Mode** |
| Need monitoring dashboards | **Production Mode** |
| Need human review UI | **Production Mode** |

---

## Feature Comparison

| Feature | Development Mode | Production Mode |
|---------|-----------------|-----------------|
| **Setup Time** | 10 minutes | 20-30 minutes |
| **Complexity** | Simple | Moderate |
| **RAM Required** | 4GB | 8-16GB |
| **Docker Required** | ❌ No | ✅ Yes |
| **Core Agents** | ✅ All 6 agents | ✅ All 6 agents |
| **ChromaDB** | ✅ Embedded | ✅ Standalone |
| **PostgreSQL** | ❌ Not needed | ✅ Included |
| **Redis Cache** | ❌ Not needed | ✅ Included |
| **Streamlit UI** | ❌ No | ✅ Yes |
| **Monitoring** | ❌ No | ✅ Prometheus + Grafana |
| **API Server** | ❌ Optional | ✅ FastAPI |
| **Suitable For** | Dev, Testing | Production, Demos |

---

## Development Mode

### What You Get
✅ All 6 agents (Extractor, Retriever, Policy Reasoner, Citation Verifier, Appeal Drafter, Executor)
✅ ChromaDB (embedded mode - no separate service)
✅ Full test suite (unit + integration + regression)
✅ Citation verification with hallucination detection
✅ Command-line testing scripts

### What You DON'T Get
❌ Web UI for human review
❌ REST API endpoints
❌ Monitoring dashboards (Prometheus/Grafana)
❌ Databases (PostgreSQL, Redis)
❌ Container orchestration

### Best For
- Local development and debugging
- Running unit and integration tests
- Validating hallucination metrics
- Quick experimentation
- CI/CD pipelines

### Commands
```bash
# Setup (5 minutes)
python -m venv .venv && source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY="your-key"

# Generate data & index
python scripts/generate_data_simple.py
python scripts/index_policies_openai.py

# Run tests
pytest tests/unit/ -v
python scripts/run_regression_suite.py
```

---

## Production Mode

### What You Get
✅ Everything from Development Mode, PLUS:
✅ FastAPI REST API server (port 8000)
✅ Streamlit Human Review UI (port 8501)
✅ PostgreSQL database (port 5432)
✅ Redis caching layer (port 6379)
✅ Prometheus metrics (port 9090)
✅ Grafana dashboards (port 3000)
✅ Container orchestration (Docker Compose)

### Best For
- Production deployment
- Stakeholder demos
- Full system validation
- Monitoring and observability
- Human-in-the-loop workflows
- API integration testing

### Commands
```bash
# Setup (10 minutes)
cp .env.example .env  # Add OPENAI_API_KEY

# Generate data & index (outside Docker)
python -m venv .venv && source .venv/bin/activate
pip install -e .
python scripts/generate_data_simple.py
python scripts/index_policies_openai.py

# Start full stack
docker-compose up -d

# Access services
open http://localhost:8000/docs  # API
open http://localhost:8501       # UI
open http://localhost:3000       # Grafana
```

---

## When to Switch?

### Start with Development Mode if:
- You're new to the system
- You want to understand how agents work
- You're running automated tests
- You have limited resources (RAM/Docker)
- You're doing local debugging

### Switch to Production Mode when:
- You need to demonstrate the full UI
- You want monitoring/dashboards
- You're deploying to staging/prod
- You need the REST API
- You want human review workflows

---

## Resource Requirements

### Development Mode
```
CPU:  2 cores (minimum)
RAM:  4GB (minimum), 8GB (recommended)
Disk: 5GB free space
Time: ~10 minutes setup
```

### Production Mode
```
CPU:  4 cores (minimum)
RAM:  8GB (minimum), 16GB (recommended)
Disk: 10GB free space
Time: ~20-30 minutes setup
```

---

## Common Issues

### Development Mode
**Issue:** "Module not found"
**Fix:** Make sure venv is activated and dependencies installed

**Issue:** ChromaDB errors
**Fix:** Delete `data/vector_store/` and re-run indexing script

**Issue:** Tests failing
**Fix:** Ensure policies are indexed first

### Production Mode
**Issue:** Port already in use
**Fix:** `docker-compose down -v` then restart

**Issue:** Services won't start
**Fix:** Check Docker has enough memory allocated (8GB min)

**Issue:** Can't access UI
**Fix:** Wait 30-60s for services to fully start, check `docker-compose logs -f`

---

## Migration Path

**From Dev to Prod:**
```bash
# You already have indexed policies in data/vector_store/
# Just start Docker stack
docker-compose up -d
```

**From Prod to Dev:**
```bash
# Stop Docker services
docker-compose down

# Use embedded ChromaDB
python scripts/test_single_claim.py
```

---

## Quick Start Commands

### Development Mode (One-Liner)
```bash
python -m venv .venv && source .venv/bin/activate && pip install -e . && \
export OPENAI_API_KEY="your-key" && \
python scripts/generate_data_simple.py && \
python scripts/index_policies_openai.py && \
pytest tests/unit/ -v
```

### Production Mode (One-Liner)
```bash
# Prerequisites: Docker installed, .env configured
python -m venv .venv && source .venv/bin/activate && pip install -e . && \
export OPENAI_API_KEY="your-key" && \
python scripts/generate_data_simple.py && \
python scripts/index_policies_openai.py && \
docker-compose up -d
```

---

**Recommendation:** Start with **Development Mode** to learn the system, then move to **Production Mode** for demos and deployment.
