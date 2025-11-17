"""
Claim-related data models and schemas.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class ClaimStatus(str, Enum):
    """Status of a healthcare claim."""

    SUBMITTED = "submitted"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    APPEALED = "appealed"
    RESUBMITTED = "resubmitted"


class DenialReason(str, Enum):
    """Common reasons for claim denial."""

    DUPLICATE_SUBMISSION = "duplicate_submission"
    CPT_MISMATCH = "cpt_mismatch"
    DOCUMENTATION_MISMATCH = "documentation_mismatch"
    ELIGIBILITY_CUTOFF = "eligibility_cutoff"
    PRIOR_AUTHORIZATION_MISSING = "prior_authorization_missing"
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    OUT_OF_NETWORK = "out_of_network"
    TIMELY_FILING_LIMIT = "timely_filing_limit"
    CODING_ERROR = "coding_error"
    INSUFFICIENT_DOCUMENTATION = "insufficient_documentation"
    OTHER = "other"


class PatientInfo(BaseModel):
    """Patient demographic and identification information."""

    model_config = ConfigDict(frozen=True)

    patient_id: str = Field(..., description="Unique patient identifier")
    # PHI fields - should be encrypted in production
    first_name_encrypted: Optional[str] = Field(None, description="Encrypted first name")
    last_name_encrypted: Optional[str] = Field(None, description="Encrypted last name")
    date_of_birth_encrypted: Optional[str] = Field(None, description="Encrypted DOB")
    member_id: str = Field(..., description="Insurance member ID")
    group_number: Optional[str] = Field(None, description="Insurance group number")


class ProviderInfo(BaseModel):
    """Healthcare provider information."""

    model_config = ConfigDict(frozen=True)

    provider_id: str = Field(..., description="Unique provider identifier")
    npi: str = Field(..., description="National Provider Identifier")
    provider_name: str = Field(..., description="Provider name or organization")
    tax_id: Optional[str] = Field(None, description="Tax identification number")


class Claim(BaseModel):
    """Core healthcare claim data structure."""

    model_config = ConfigDict(frozen=True)

    claim_id: UUID = Field(default_factory=uuid4, description="Unique claim identifier")
    external_claim_number: str = Field(..., description="External claim reference number")

    # Patient and provider
    patient: PatientInfo
    provider: ProviderInfo

    # Claim details
    service_date: date = Field(..., description="Date of service")
    submission_date: datetime = Field(
        default_factory=datetime.utcnow, description="Claim submission timestamp"
    )

    # Billing information
    cpt_codes: list[str] = Field(..., description="Current Procedural Terminology codes")
    icd_codes: list[str] = Field(..., description="International Classification of Diseases codes")
    total_billed_amount: Decimal = Field(..., description="Total amount billed")

    # Claim status
    status: ClaimStatus = Field(default=ClaimStatus.SUBMITTED)

    # Metadata
    payor_name: str = Field(..., description="Insurance payor name")
    policy_number: str = Field(..., description="Insurance policy number")


class ClaimDenial(BaseModel):
    """Claim denial with reason and supporting information."""

    model_config = ConfigDict(frozen=True)

    denial_id: UUID = Field(default_factory=uuid4, description="Unique denial identifier")
    claim_id: UUID = Field(..., description="Reference to denied claim")
    claim_number: Optional[str] = Field(None, description="Human-readable claim number (e.g., CLM-2024-001234)")

    # Denial details
    denial_date: datetime = Field(
        default_factory=datetime.utcnow, description="Denial timestamp"
    )
    denial_reason: DenialReason = Field(..., description="Primary denial reason")
    denial_reason_text: str = Field(..., description="Detailed denial explanation")

    # Source document
    source_document_id: Optional[UUID] = Field(
        None, description="Reference to source denial document"
    )
    source_document_path: Optional[str] = Field(
        None, description="Path to source PDF/document"
    )

    # Processing metadata
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Extraction confidence score"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow, description="Extraction timestamp"
    )

    # Additional context
    payor_contact: Optional[str] = Field(None, description="Payor contact information")
    appeal_deadline: Optional[date] = Field(None, description="Appeal submission deadline")
    additional_notes: Optional[str] = Field(None, description="Additional context")
