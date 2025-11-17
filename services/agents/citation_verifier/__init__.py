"""
Citation Verifier Agent - verifies all claims have valid source citations.
Critical for hallucination prevention and audit compliance.
"""

from .citation_verifier_agent import CitationVerifierAgent, VerificationResult

__all__ = ["CitationVerifierAgent", "VerificationResult"]
