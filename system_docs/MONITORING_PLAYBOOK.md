# Monitoring & Postmortem Playbook

**System:** Claim Triage & Resolution Agentic System
**Version:** 1.0
**Last Updated:** 2025-11-17

---

## 1. Key Metrics & Alert Thresholds

### Critical KPIs (Real-time Monitoring)

| Metric | Definition | Threshold | Alert Level | Action |
|--------|------------|-----------|-------------|--------|
| **hallucination_rate** | Failed citations / total citations | > 2% | CRITICAL | Block deployments, escalate immediately |
| **evidence_coverage** | Verified citations / total claims | < 85% | HIGH | Review appeal quality, retrain retriever |
| **false_accept_rate** | Incorrect approvals / total decisions | > 5% | HIGH | Halt auto-approval, enable 100% human review |
| **human_override_rate** | Manual rejections / auto-approvals | > 15% | MEDIUM | Review policy reasoner accuracy |
| **avg_latency** | P95 end-to-end processing time | > 120s | MEDIUM | Scale infrastructure, optimize retrievals |
| **cost_per_case** | Total token cost / cases processed | > $2.50 | LOW | Review caching strategy, prompt optimization |

### System Health Metrics

- **API Availability:** > 99.9% uptime
- **Error Rate:** < 5% across all agents
- **Retrieval Accuracy:** Top-5 relevance > 90%
- **PHI Exposure Events:** 0 (zero tolerance)

---

## 2. Canary & Rollback Plan

### Model Update Deployment Strategy

**Phase 1: Canary Testing (10% traffic, 24 hours)**
1. Deploy new model version to canary environment
2. Route 10% of production traffic to canary
3. Monitor critical metrics:
   - Hallucination rate must remain < 2%
   - Evidence coverage must remain > 85%
   - Latency increase must be < 20%
4. Run regression suite on canary deployment
5. **GO/NO-GO Decision:** Requires approval from 2+ engineers

**Phase 2: Gradual Rollout (if canary passes)**
- 25% traffic (12 hours) → 50% traffic (12 hours) → 100% traffic
- Automated rollback if ANY critical metric breaches threshold

**Phase 3: Rollback Procedure**
```bash
# Immediate rollback (< 2 minutes)
kubectl set image deployment/claim-triage-api app=previous-version
docker-compose restart --scale api=0 && docker-compose up -d --scale api=3

# Verify rollback
curl http://localhost:8000/health | jq '.model_version'
```

**Rollback Triggers (Automatic):**
- Hallucination rate > 2% for 5 consecutive minutes
- Error rate > 10% for 3 minutes
- P95 latency > 180s for 10 minutes
- PHI exposure event detected (instant rollback)

---

## 3. Incident Runbook: Hallucination Detected

### Severity: CRITICAL (P0)

**Detection:**
- Alert: "Hallucination rate exceeded 2% threshold"
- Source: Citation Verifier Agent metrics
- Example: 3 out of 120 appeals contained unverified policy citations

**Immediate Response (< 5 minutes):**
1. **STOP AUTO-APPROVALS:** Enable 100% human review gate
   ```bash
   kubectl set env deployment/claim-triage-api ENABLE_AUTO_APPROVAL=false
   ```
2. **Notify stakeholders:** Page on-call engineer, notify compliance team
3. **Isolate affected cases:** Query audit logs for recent hallucinated appeals
   ```sql
   SELECT claim_id, appeal_id, citation_id
   FROM audit_events
   WHERE hallucination_detected = true
   AND timestamp > NOW() - INTERVAL '1 hour';
   ```

**Investigation (< 30 minutes):**
1. **Retrieve logs:** Download LangSmith traces for failing cases
2. **Identify root cause:**
   - Model degradation (OpenAI API issue)?
   - Retrieval failure (vector DB corruption)?
   - Prompt injection attack?
   - Policy document update conflict?
3. **Assess impact:** Identify affected appeals submitted to payers
   ```bash
   python scripts/audit_affected_appeals.py --since="1 hour ago"
   ```

**Mitigation (< 2 hours):**
- **If model issue:** Rollback to previous LLM version
- **If retrieval issue:** Rebuild vector index, verify policy doc integrity
- **If prompt injection:** Apply input sanitization patch, re-run affected claims
- **If policy conflict:** Resolve contradictory policy sections, re-index

**Remediation (< 24 hours):**
1. Manually review ALL affected appeals with clinical experts
2. Issue corrections to payers if incorrect appeals were submitted
3. Document incident in postmortem report
4. Update adversarial test suite with new attack vector

**Required Logs:**
- LangSmith trace IDs for hallucinated appeals
- PostgreSQL audit logs (PHI access trail)
- Redis cache state at time of incident
- Vector DB query logs (retrieval accuracy)

**Stakeholders:**
- **Incident Commander:** On-call SRE
- **Engineering:** AI/ML team lead
- **Compliance:** HIPAA compliance officer
- **Product:** Claims operations manager

---

## 4. Monitoring Dashboard (Grafana)

### Critical Panels
1. **Hallucination Rate (30-min rolling window)** - Line chart
2. **Evidence Coverage** - Gauge (target: >85%)
3. **Processing Latency (P50/P95/P99)** - Histogram
4. **Agent Success Rates** - Stacked bar chart per agent
5. **Cost Tracking** - Token usage + cost per case
6. **PHI Exposure Events** - Counter (must always be 0)

### Alert Rules (Prometheus)
```yaml
- alert: HallucinationRateHigh
  expr: hallucination_rate > 0.02
  for: 5m
  severity: critical

- alert: EvidenceCoverageLow
  expr: evidence_coverage < 0.85
  for: 10m
  severity: high

- alert: PHIExposureDetected
  expr: phi_exposure_events > 0
  for: 0m  # Instant alert
  severity: critical
```

---

## 5. Postmortem Template

**Incident Date:** [YYYY-MM-DD]
**Incident ID:** [INC-XXXX]
**Severity:** [P0/P1/P2]
**Duration:** [Time to detection → Time to resolution]

**Summary:**
- Brief description of incident (1-2 sentences)

**Impact:**
- Claims affected: [Number]
- Appeals submitted incorrectly: [Number]
- PHI exposure: [Yes/No]

**Root Cause:**
- Technical cause (model degradation, retrieval failure, etc.)

**Timeline:**
- [HH:MM] Incident began
- [HH:MM] Alert triggered
- [HH:MM] Incident acknowledged
- [HH:MM] Mitigation applied
- [HH:MM] Incident resolved

**Lessons Learned:**
1. What went well?
2. What went wrong?
3. Where were we lucky?

**Action Items:**
- [ ] Add adversarial test case for this scenario
- [ ] Update runbook with new mitigation steps
- [ ] Improve alert sensitivity for early detection
- [ ] Train team on new failure mode

**Preventive Measures:**
- Code changes required (link to PRs)
- Process improvements
- Monitoring enhancements

---

## 6. On-Call Escalation Path

**L1 (Auto-Alerts):** Prometheus → PagerDuty → On-call SRE
**L2 (Critical):** On-call SRE → AI/ML Team Lead
**L3 (Compliance):** Team Lead → HIPAA Officer + VP Engineering
**L4 (Executive):** VP Engineering → CTO (for regulatory incidents)

**Contact Directory:**
- On-call SRE: pagerduty.com/claim-triage
- AI/ML Team Lead: ml-team-lead@company.com
- HIPAA Officer: compliance@company.com

---

**Document Owner:** SRE Team
**Review Cadence:** Monthly (or after every P0 incident)
