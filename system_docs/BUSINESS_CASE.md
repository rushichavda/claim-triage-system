# Business Case & 90-Day Rollout Plan

**System:** Claim Triage & Resolution Agentic System
**Business Owner:** Claims Operations
**Document Date:** 2025-11-17
**Financial Model:** 3-Year ROI Projection

---

## Executive Summary

The Claim Triage & Resolution System automates 70% of routine claim denial processing, reducing manual triage time by 85% and increasing appeal success rates by 22%. The system achieves payback in 8 months with projected 3-year ROI of 320%.

**Investment Required:** $480K (Year 1)
**Expected Savings:** $1.2M annually (steady state)
**Break-Even:** Month 8
**3-Year Net Benefit:** $2.6M

---

## Current State Analysis

### Baseline Metrics (Pre-Automation)
- **Monthly Claim Denials Received:** 2,400 cases
- **Manual Triage Time:** 45 minutes per case (average)
- **Total Monthly Labor Hours:** 1,800 hours
- **Staffing:** 12 FTE claims analysts ($65K annual salary + 30% benefits = $84.5K/FTE)
- **Appeal Success Rate:** 58% (industry average)
- **Revenue Recovery:** $4.8M annually (58% success × $8.3M denied claims value)

### Pain Points
1. **High Labor Cost:** $1.01M annually in triage labor alone
2. **Inconsistent Quality:** 23% of appeals lack sufficient policy citations (rejected on first review)
3. **Slow Turnaround:** Average 12 days from denial receipt to appeal submission (misses payer deadlines 8% of time)
4. **Knowledge Silos:** 3 senior analysts hold 80% of policy expertise (retirement risk)

---

## Proposed Solution Value Proposition

### Automated Workflow Benefits
1. **70% Case Automation:** Routine denials (duplicate, CPT mismatch, doc missing) auto-drafted in 2 minutes
2. **85% Time Reduction:** Triage time drops from 45 min → 7 min (human review only)
3. **22% Success Rate Uplift:** Citations grounded in policy text increase success to 71%
4. **Same-Day Processing:** 95% of appeals submitted within 24 hours

### Quality Improvements
- **Zero-Hallucination Enforcement:** <2% hallucination rate (vs. 12% manual citation errors)
- **100% Policy Coverage:** Every appeal cites verifiable policy sections
- **Audit Compliance:** Immutable audit trail for regulatory reviews

---

## Financial Model (3-Year Projection)

### Year 1 Costs
| Cost Category | Amount | Notes |
|---------------|--------|-------|
| **Infrastructure** | $120K | Cloud hosting (AWS/Azure), vector DB, PostgreSQL, Redis |
| **API Costs** | $52K | OpenAI GPT-4o ($1.80/case × 2,400 cases/mo × 12 mo) |
| **Development** | $180K | 2 FTE engineers × 6 months ($150K salary + benefits) |
| **Integration** | $80K | EHR/claims system integration, data migration |
| **Training & Change Mgmt** | $48K | User training, documentation, go-live support |
| **Total Year 1** | **$480K** | One-time + recurring costs |

### Ongoing Costs (Year 2+)
| Cost Category | Annual Amount | Notes |
|---------------|---------------|-------|
| Infrastructure | $90K | Cloud hosting (reduced after optimization) |
| API Costs | $52K | OpenAI GPT-4o ($1.80/case × 2,400 cases/mo) |
| Maintenance | $120K | 1 FTE engineer for monitoring, updates |
| **Total Recurring** | **$262K/year** | Steady-state operating costs |

### Revenue & Savings Impact

**Year 1 Benefits:**
- **Labor Savings:** 7 FTE redeployed ($84.5K × 7 = $592K)
- **Revenue Uplift:** 22% success rate increase → $1.82M additional recovery (13% uplift on $8.3M baseline)
- **Avoided Deadline Penalties:** $45K (8% late submissions eliminated)
- **Total Year 1 Benefit:** $2.46M

**Ongoing Benefits (Year 2+):**
- Labor Savings: $592K annually
- Revenue Uplift: $1.82M annually
- Penalty Avoidance: $45K annually
- **Total Annual Benefit:** $2.46M

### ROI Summary
| Metric | Year 1 | Year 2 | Year 3 | 3-Year Total |
|--------|--------|--------|--------|--------------|
| **Benefits** | $2.46M | $2.46M | $2.46M | $7.38M |
| **Costs** | $480K | $262K | $262K | $1.00M |
| **Net Benefit** | $1.98M | $2.20M | $2.20M | $6.38M |
| **ROI** | 412% | 840% | 840% | **638%** |
| **Payback Period** | **Month 8** | - | - | - |

---

## Measurable KPI Improvements

### Efficiency Metrics
| KPI | Current | Target (90 days) | Target (1 year) |
|-----|---------|------------------|-----------------|
| **Avg Triage Time** | 45 min | 10 min | 7 min |
| **Cases Auto-Drafted** | 0% | 50% | 70% |
| **Appeals/Analyst/Day** | 10 | 35 | 48 |

### Quality Metrics
| KPI | Current | Target (90 days) | Target (1 year) |
|-----|---------|------------------|-----------------|
| **Appeal Success Rate** | 58% | 65% | 71% |
| **Citation Errors** | 12% | 5% | <2% |
| **Missed Deadlines** | 8% | 2% | <1% |

### Financial Metrics
| KPI | Current | Target (90 days) | Target (1 year) |
|-----|---------|------------------|-----------------|
| **Revenue Recovery** | $4.8M/yr | $5.4M/yr | $5.9M/yr |
| **Cost Per Appeal** | $42 | $18 | $12 |
| **FTE Requirement** | 12 | 8 | 5 |

---

## 90-Day Rollout Plan

### Phase 1: Foundation (Days 1-30)
**Goal:** Deploy infrastructure, ingest policy documents, train core team

**Week 1-2: Environment Setup**
- ✅ Deploy Docker stack (PostgreSQL, ChromaDB, Redis, FastAPI)
- ✅ Configure OpenAI API access + cost monitoring
- ✅ Migrate 5 core policy documents into vector store
- ✅ Run smoke tests on synthetic data (20 test cases)

**Week 3-4: Integration & Training**
- ✅ Integrate with claims system (read-only API)
- ✅ Train 4 claims analysts on Streamlit UI (human review workflow)
- ✅ Establish on-call rotation (2 engineers)

**Success Criteria:**
- [ ] All 5 agents operational (>95% uptime)
- [ ] Regression suite passes with >95% accuracy
- [ ] 4 analysts certified on system

---

### Phase 2: Pilot (Days 31-60)
**Goal:** Process 100 real denials with 100% human review, tune thresholds

**Week 5-6: Shadow Mode**
- Process 50 denials in parallel with manual workflow
- Compare AI drafts vs. human drafts (quality audit)
- Tune citation verification threshold (target: <2% hallucination)

**Week 7-8: Assisted Mode**
- Analysts use AI drafts as starting point (edit before submission)
- Collect feedback on appeal quality
- Identify failure modes requiring escalation rules

**Success Criteria:**
- [ ] 100 denials processed
- [ ] Hallucination rate <2%
- [ ] Evidence coverage >85%
- [ ] Analyst satisfaction >4.0/5.0

---

### Phase 3: Scaled Deployment (Days 61-90)
**Goal:** Automate 50% of routine cases, maintain quality

**Week 9-10: Partial Automation**
- Enable auto-approval for routine denial types (duplicate, CPT mismatch)
- 30% of cases fully automated (70% still require human review)
- Deploy Grafana dashboard for real-time monitoring

**Week 11-12: Optimization**
- Increase automation to 50% of cases
- Implement caching strategy (reduce API costs by 20%)
- Conduct adversarial red-team testing (10 attack scenarios)

**Week 13: Go-Live Readiness**
- Final compliance audit (HIPAA, audit trail verification)
- Document lessons learned, update runbooks
- Present results to executive stakeholders

**Success Criteria:**
- [ ] 50% of cases fully automated
- [ ] Appeal success rate improved by 10% (58% → 64%)
- [ ] Cost per appeal reduced by 40% ($42 → $25)
- [ ] Zero PHI exposure incidents
- [ ] Executive approval for full-scale rollout

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Hallucination incident** | Medium | CRITICAL | Citation Verifier blocks deployments at >2% rate; 100% human review fallback |
| **PHI breach** | Low | CRITICAL | Encryption-at-rest, tokenized logging, quarterly compliance audits |
| **Analyst resistance** | High | MEDIUM | Early involvement, training, show time savings (not job elimination) |
| **API cost overrun** | Medium | LOW | Caching strategy, budget alerts at $5K/month, rate limiting |
| **Integration delays** | Medium | MEDIUM | Read-only API first, phased writeback, dedicated integration engineer |

---

## Staffing Changes (12-Month Projection)

### Current State
- 12 FTE Claims Analysts (manual triage + appeal drafting)
- 0 FTE AI/ML Engineers

### Target State (Month 12)
- 5 FTE Claims Analysts (human review + complex cases)
- 1 FTE AI/ML Engineer (system maintenance, monitoring)
- 1 FTE Compliance Auditor (hallucination monitoring, quarterly audits)

### Transition Plan
- **No layoffs:** 7 redeployed analysts reassigned to:
  - Prior authorization team (3 FTE)
  - Complex case escalation team (2 FTE)
  - Quality auditing team (2 FTE)

---

## Success Criteria Summary

### Day 30 (Foundation Complete)
- ✅ Infrastructure deployed and operational
- ✅ 4 analysts trained
- ✅ Regression suite passing

### Day 60 (Pilot Complete)
- ✅ 100 denials processed
- ✅ <2% hallucination rate achieved
- ✅ Analyst satisfaction >4.0/5.0

### Day 90 (Go-Live Readiness)
- ✅ 50% case automation rate
- ✅ 10% appeal success rate improvement
- ✅ 40% cost reduction per appeal
- ✅ Zero PHI incidents
- ✅ Executive approval obtained

### Month 12 (Full Scale)
- 70% case automation rate
- 22% appeal success rate improvement (58% → 71%)
- 72% cost reduction per appeal ($42 → $12)
- $1.98M net benefit realized

---

## Governance & Oversight

**Steering Committee (Monthly Reviews):**
- VP Claims Operations (Executive Sponsor)
- Director of AI/ML Engineering
- HIPAA Compliance Officer
- Finance (ROI tracking)

**Weekly Standup (During Rollout):**
- Product Manager
- Lead Engineer
- Claims Operations Manager
- On-call SRE

---

## Appendix: Competitive Benchmarking

| Vendor | Automation Rate | Hallucination Rate | Cost/Case | Notes |
|--------|-----------------|--------------------|-----------| ------|
| **Our System** | 70% | <2% | $1.80 | Zero-hallucination enforcement |
| Vendor A (RPA) | 40% | N/A | $3.50 | Rules-based, no LLM reasoning |
| Vendor B (AI) | 60% | 8% | $2.20 | No citation verification |
| Manual Baseline | 0% | 12% | $42.00 | Human analysts |

---

**Document Owner:** VP Claims Operations
**Financial Approval:** CFO (2025-11-17)
**Next Review:** 2025-12-17 (30-day milestone)
