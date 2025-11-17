"""
Data schemas and contracts for the claim triage system.
All structured data types used across services.
"""

from .claim import (
    Claim,
    ClaimDenial,
    ClaimStatus,
    DenialReason,
    PatientInfo,
    ProviderInfo,
)
from .citation import Citation, CitationSpan, SourceDocument
from .audit import AuditEvent, AuditEventType, AuditLog
from .decision import Decision, DecisionType, DecisionRationale
from .appeal import Appeal, AppealDraft, AppealStatus

__all__ = [
    # Claim schemas
    "Claim",
    "ClaimDenial",
    "ClaimStatus",
    "DenialReason",
    "PatientInfo",
    "ProviderInfo",
    # Citation schemas
    "Citation",
    "CitationSpan",
    "SourceDocument",
    # Audit schemas
    "AuditEvent",
    "AuditEventType",
    "AuditLog",
    # Decision schemas
    "Decision",
    "DecisionType",
    "DecisionRationale",
    # Appeal schemas
    "Appeal",
    "AppealDraft",
    "AppealStatus",
]
