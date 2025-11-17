"""
Extractor Agent implementation using OpenAI + Instructor for structured extraction.
Extracts claim denial data with confidence scoring.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from services.ingest.pdf_parser import ParsedDocument
from services.shared.schemas.audit import AuditEvent, AuditEventType
from services.shared.schemas.claim import ClaimDenial, DenialReason, PatientInfo, ProviderInfo
from services.shared.utils import get_logger, get_settings

logger = get_logger(__name__)


class ExtractedClaimData(BaseModel):
    """Structured extraction output with confidence scores."""

    # Patient info
    patient_id: str = Field(..., description="Patient identifier")
    member_id: str = Field(..., description="Insurance member ID")
    patient_first_name: Optional[str] = Field(None, description="Patient first name")
    patient_last_name: Optional[str] = Field(None, description="Patient last name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")

    # Provider info
    provider_id: str = Field(..., description="Provider identifier")
    npi: str = Field(..., description="National Provider Identifier")
    provider_name: str = Field(..., description="Provider name")

    # Claim details
    external_claim_number: str = Field(..., description="External claim number")
    service_date: str = Field(..., description="Date of service (YYYY-MM-DD)")
    cpt_codes: list[str] = Field(..., description="CPT codes")
    icd_codes: list[str] = Field(default_factory=list, description="ICD codes")
    total_billed_amount: float = Field(..., description="Total billed amount")

    # Denial info
    denial_reason: str = Field(..., description="Primary denial reason")
    denial_reason_text: str = Field(..., description="Detailed denial explanation")
    payor_name: str = Field(..., description="Insurance payor name")
    policy_number: str = Field(..., description="Policy number")
    appeal_deadline: Optional[str] = Field(None, description="Appeal deadline (YYYY-MM-DD)")

    # Confidence scores (0.0 to 1.0)
    extraction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall extraction confidence"
    )
    field_confidence: dict[str, float] = Field(
        default_factory=dict, description="Per-field confidence scores"
    )


class ExtractionResult(BaseModel):
    """Result from extractor agent with audit info."""

    extracted_data: ExtractedClaimData
    claim_denial: ClaimDenial
    audit_events: list[AuditEvent]
    processing_time_ms: float


class ExtractorAgent:
    """
    Extractor agent using LLM with structured output.
    Extracts claim denial data with confidence scoring.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logger.bind(agent="extractor")

        # Initialize OpenAI client with Instructor
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=self.settings.openai_api_key)
        )

    async def extract_claim_denial(
        self, parsed_doc: ParsedDocument, document_id: UUID
    ) -> ExtractionResult:
        """
        Extract claim denial data from parsed document.

        Args:
            parsed_doc: Parsed PDF document
            document_id: UUID of the source document

        Returns:
            ExtractionResult with extracted data and audit trail
        """
        start_time = datetime.utcnow()
        audit_events = []

        self.logger.info(
            "starting_extraction",
            document_id=str(document_id),
            total_pages=parsed_doc.total_pages,
        )

        # Create audit event for extraction start
        audit_events.append(
            AuditEvent(
                event_type=AuditEventType.CLAIM_EXTRACTED,
                document_id=document_id,
                agent_name="extractor_agent",
                description="Starting claim denial extraction",
                metadata={"document_path": parsed_doc.source_path, "pages": parsed_doc.total_pages},
            )
        )

        try:
            # Extract structured data using LLM
            extracted_data = await self._llm_extract(parsed_doc.full_text)

            # Map denial reason to enum
            denial_reason = self._map_denial_reason(extracted_data.denial_reason)

            # Create ClaimDenial object
            claim_denial = ClaimDenial(
                claim_id=parsed_doc.document_id,  # Using doc ID as claim ID for now
                claim_number=extracted_data.external_claim_number,
                denial_reason=denial_reason,
                denial_reason_text=extracted_data.denial_reason_text,
                source_document_id=document_id,
                source_document_path=parsed_doc.source_path,
                confidence_score=extracted_data.extraction_confidence,
                payor_contact=None,
                appeal_deadline=None,  # TODO: Parse date string
            )

            # Success audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.EXTRACTION_VALIDATED,
                    document_id=document_id,
                    agent_name="extractor_agent",
                    description="Claim denial extracted successfully",
                    success=True,
                    metadata={
                        "confidence": extracted_data.extraction_confidence,
                        "claim_number": extracted_data.external_claim_number,
                        "denial_reason": denial_reason.value,
                    },
                )
            )

            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "extraction_complete",
                document_id=str(document_id),
                confidence=extracted_data.extraction_confidence,
                processing_time_ms=processing_time_ms,
            )

            return ExtractionResult(
                extracted_data=extracted_data,
                claim_denial=claim_denial,
                audit_events=audit_events,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            self.logger.error("extraction_failed", document_id=str(document_id), error=str(e))

            # Error audit event
            audit_events.append(
                AuditEvent(
                    event_type=AuditEventType.SYSTEM_ERROR,
                    document_id=document_id,
                    agent_name="extractor_agent",
                    description="Claim denial extraction failed",
                    success=False,
                    error_message=str(e),
                )
            )

            raise

    async def _llm_extract(self, full_text: str) -> ExtractedClaimData:
        """
        Use LLM with structured output to extract claim data.

        Args:
            full_text: Full text from denial document

        Returns:
            ExtractedClaimData with confidence scores
        """
        # Truncate text if too long (keep first 6000 chars)
        text_input = full_text[:6000] if len(full_text) > 6000 else full_text

        extraction_prompt = f"""You are an expert medical billing specialist. Extract structured claim denial information from the following document.

For each field, provide your confidence level (0.0 to 1.0) in the extraction accuracy.

Document Text:
{text_input}

Extract all claim information, patient details, provider information, denial reason, and billing codes.
If a field is not found, use reasonable defaults or "UNKNOWN" for string fields.
"""

        try:
            # Use instructor to get structured output
            extracted_data = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                response_model=ExtractedClaimData,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical billing expert that extracts structured data from claim denial documents.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
            )

            return extracted_data

        except Exception as e:
            self.logger.error("llm_extraction_error", error=str(e))
            raise ValueError(f"LLM extraction failed: {e}") from e

    def _map_denial_reason(self, reason_text: str) -> DenialReason:
        """
        Map extracted denial reason text to DenialReason enum.

        Args:
            reason_text: Denial reason from extraction

        Returns:
            DenialReason enum value
        """
        reason_lower = reason_text.lower()

        # Simple keyword mapping
        mappings = {
            "duplicate": DenialReason.DUPLICATE_SUBMISSION,
            "cpt": DenialReason.CPT_MISMATCH,
            "code": DenialReason.CODING_ERROR,
            "documentation": DenialReason.DOCUMENTATION_MISMATCH,
            "insufficient": DenialReason.INSUFFICIENT_DOCUMENTATION,
            "eligibility": DenialReason.ELIGIBILITY_CUTOFF,
            "authorization": DenialReason.PRIOR_AUTHORIZATION_MISSING,
            "prior auth": DenialReason.PRIOR_AUTHORIZATION_MISSING,
            "medical necessity": DenialReason.NOT_MEDICALLY_NECESSARY,
            "medically necessary": DenialReason.NOT_MEDICALLY_NECESSARY,
            "out of network": DenialReason.OUT_OF_NETWORK,
            "timely": DenialReason.TIMELY_FILING_LIMIT,
            "filing": DenialReason.TIMELY_FILING_LIMIT,
        }

        for keyword, denial_type in mappings.items():
            if keyword in reason_lower:
                return denial_type

        # Default to OTHER if no match
        return DenialReason.OTHER
