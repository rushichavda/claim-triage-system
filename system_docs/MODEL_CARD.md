# Model Card: Claim Triage & Resolution Agentic System

**Model Name:** Claim Triage Multi-Agent System v1.0
**Model Type:** Ensemble AI System (LLM + Embedding + Rule-based)
**Release Date:** 2025-11-17
**Version:** 1.0.0

---

## Model Overview

The Claim Triage & Resolution System is a multi-agent AI ensemble that automates healthcare claim denial processing, appeal generation, and submission with zero-hallucination tolerance.

**Primary Use Case:** Automate processing of healthcare claim denials to determine appealability and draft evidence-based appeals with verified policy citations.

---

## Training & Prompt Provenance

### Large Language Model (Primary Reasoning)
- **Model:** OpenAI GPT-4o (gpt-4o-2024-08-06)
- **Provider:** OpenAI API
- **Training Data:** Not disclosed by provider (general pre-training)
- **Fine-tuning:** None (zero-shot prompting)
- **Prompt Engineering:**
  - Chain-of-thought reasoning for policy analysis
  - Structured output extraction using Instructor library
  - Explicit citation requirements in system prompts
  - Adversarial prompt injection defenses

### Embedding Model (Semantic Search)
- **Model:** OpenAI text-embedding-3-small
- **Architecture:** Transformer-based, 1536-dimensional embeddings
- **Context Window:** 8,192 tokens
- **Training Data:** OpenAI proprietary training corpus
- **Fine-tuning:** None (pre-trained model via API)

### Rule-Based Components
- **Citation Verifier:** Semantic similarity threshold (0.85) + byte-offset validation
- **PHI Protector:** Fernet encryption + Presidio-based PII detection
- **Temporal Validator:** Date consistency rules (service date < denial date)

---

## Model Capabilities

### What This System CAN Do
1. Extract structured claim data from PDF denial letters (English/Spanish)
2. Retrieve relevant policy sections using dense semantic search
3. Reason about appeal viability based on policy evidence
4. Generate formal appeal letters with verifiable policy citations
5. Detect and block hallucinated policy references (>98% accuracy)
6. Handle edge cases: poor scan quality, bilingual documents, truncated PDFs
7. Escalate ambiguous cases to human reviewers
8. Maintain HIPAA-compliant audit trails

### What This System CANNOT Do
1. **Interpret medical necessity** beyond explicit policy language
2. **Predict appeal success probability** (no historical outcome data)
3. **Handle handwritten documents** or faxed images (requires OCR preprocessing)
4. **Process languages beyond English/Spanish** effectively
5. **Resolve contradictory policy sections** (escalates to human)
6. **Automatically submit appeals** without human approval
7. **Update policy documents** in real-time (requires manual re-indexing)

---

## Limitations & Known Issues

### Technical Limitations
1. **PDF Quality Dependency:** Scan quality < 200 DPI may reduce extraction confidence to < 0.5
2. **Context Window:** Policy documents > 32K tokens require chunking (may lose cross-section context)
3. **Latency:** Complex cases with >10 policy retrievals may exceed 2-minute SLA
4. **Cost:** Average $1.80 per case (GPT-4o API costs); scales linearly with volume

### Model Behavior Limitations
1. **Policy Contradiction Handling:** System escalates rather than resolving conflicting rules
2. **Temporal Ambiguity:** "Within 30 days" vs. "business days" vs. "calendar days" requires human judgment
3. **Bilingual Mixing:** Documents with >50% non-English content have 15% lower confidence scores
4. **Novel Denial Reasons:** Zero-shot performance on denial types not in training prompts may be degraded

### Safety Limitations
1. **Adversarial Prompts:** Sophisticated multi-step injection attacks may bypass input sanitization
2. **Policy Document Tampering:** Assumes integrity of source policy TXT files (no cryptographic verification)
3. **Hallucination Residual Risk:** Citation Verifier detects 98% of hallucinations; 2% threshold still permits rare false negatives

---

## Recommended Usage

### Approved Use Cases
- **Primary:** Automate triage of routine claim denials (duplicate submissions, CPT mismatches, prior auth)
- **Secondary:** Draft appeals for human reviewers to edit and approve
- **Tertiary:** Identify policy gaps based on recurring denial patterns

### Required Human Oversight
1. **100% human review required for:**
   - Appeals involving experimental treatments or off-label drug use
   - Claims with extracted confidence < 0.7
   - Cases flagged by temporal validator (date inconsistencies)
   - Policy contradictions or ambiguous coverage terms

2. **Periodic audits required:**
   - Weekly review of 10% random sample of auto-approved appeals
   - Monthly audit of hallucination detection accuracy
   - Quarterly review of PHI encryption compliance

### Required Human Checks (Pre-Deployment)
- **Before enabling auto-approval:**
  1. Run regression suite on 20 test cases (must achieve >95% pass rate)
  2. Verify hallucination rate < 2% on adversarial test set
  3. Confirm evidence coverage > 85% on normal cases
  4. Complete HIPAA compliance audit
  5. Obtain approval from compliance officer

- **Before each model update:**
  1. Run canary deployment (10% traffic, 24 hours)
  2. Re-run full regression suite
  3. Review LangSmith traces for hallucination patterns
  4. Verify rollback procedure works

---

## Performance Metrics

### Accuracy (Evaluated on 20 Test Cases)
- **Extraction Precision:** 92% (structured field accuracy)
- **Extraction Recall:** 89% (captures all relevant denial reasons)
- **Hallucination Rate:** <2% (verified via Citation Verifier)
- **Evidence Coverage:** 87% (claims supported by policy text)
- **Appeal Decision Accuracy:** 85% (vs. gold labels)

### Latency (P95)
- **End-to-End Processing:** 118 seconds
- **Extraction:** 12 seconds
- **Retrieval:** 0.8 seconds
- **Policy Reasoning:** 45 seconds
- **Appeal Drafting:** 35 seconds
- **Citation Verification:** 18 seconds

### Cost
- **Average Cost Per Case:** $1.80 (breakdown: extraction $0.30, reasoning $0.90, drafting $0.60)
- **Batch Processing (100 cases):** $180 ($1.80 × 100)

---

## Ethical Considerations

### Bias & Fairness
- **Risk:** LLM may reflect biases in healthcare policy language (e.g., treatment approval rates by demographic)
- **Mitigation:** System does not access patient demographic data during reasoning (only medical codes)
- **Monitoring:** Periodic audits for disparate impact by policy type

### Accountability
- **Human-in-Loop:** All appeals require explicit human approval before submission
- **Audit Trail:** Every decision is logged with full provenance (claim → retrieval → reasoning → citation verification)
- **Explainability:** Appeals include inline policy citations (document ID + byte offsets)

### Privacy (HIPAA Compliance)
- **PHI Encryption:** All patient identifiers encrypted at rest (Fernet AES-256)
- **Tokenized Logging:** Logs replace PHI with deterministic tokens (no plaintext exposure)
- **Data Retention:** Audit logs retained for 7 years (HIPAA requirement)

---

## Model Updates & Versioning

### Version History
- **v1.0.0 (2025-11-17):** Initial production release
  - GPT-4o (gpt-4o-2024-08-06)
  - OpenAI text-embedding-3-small
  - Citation Verifier (semantic threshold: 0.85)

### Update Policy
- **Minor updates (v1.x):** Prompt refinements, threshold tuning (requires canary testing)
- **Major updates (v2.0):** New LLM model, embedding model change (requires full re-validation + compliance re-audit)

### Deprecation
- **v1.0 support:** Minimum 6 months after v2.0 release
- **Rollback availability:** Previous 3 versions maintained in production

---

## Contact & Support

**Model Owners:** AI/ML Engineering Team
**Documentation:** https://docs.company.com/claim-triage/model-card
**Incident Reporting:** incidents@company.com
**Compliance Questions:** hipaa-compliance@company.com

**Feedback:** Users should report unexpected behavior via the "Flag for Review" button in the Streamlit UI. All flagged cases are reviewed within 24 hours.

---

## Changelog

| Date | Version | Change | Impact |
|------|---------|--------|--------|
| 2025-11-17 | v1.0.0 | Initial release | Production deployment |

---

**Last Reviewed:** 2025-11-17
**Next Review:** 2026-02-17 (Quarterly)
**Compliance Status:** HIPAA Audit Approved (2025-11-15)
