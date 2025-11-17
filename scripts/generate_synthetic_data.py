"""
Generate synthetic policy documents and claim denial PDFs for testing.
Uses LLM to create realistic healthcare claim scenarios.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT

from services.shared.utils import get_settings, setup_logging, get_logger

setup_logging(log_level="INFO", json_logs=False)
logger = get_logger(__name__)


class SyntheticDataGenerator:
    """Generate synthetic healthcare data for testing."""

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.output_dir = Path("data")
        self.policy_dir = self.output_dir / "policy_docs"
        self.test_cases_dir = self.output_dir / "test_cases"

        # Create directories
        self.policy_dir.mkdir(parents=True, exist_ok=True)
        (self.test_cases_dir / "synthetic").mkdir(parents=True, exist_ok=True)
        (self.test_cases_dir / "adversarial").mkdir(parents=True, exist_ok=True)
        (self.test_cases_dir / "edge_cases").mkdir(parents=True, exist_ok=True)

    async def generate_policy_documents(self) -> list[dict]:
        """Generate 5 realistic policy documents."""

        policies = [
            {
                "name": "HealthGuard_Prior_Authorization_Policy_2024.pdf",
                "type": "prior_authorization",
                "prompt": """Generate a detailed healthcare insurance prior authorization policy document (2-3 pages).

Include:
- Policy number and effective date
- Services requiring prior authorization
- Emergency exceptions (24-hour emergency window)
- Approval process and timelines
- Specific CPT codes that require authorization
- Medical necessity criteria
- Appeals process

Make it realistic with specific policy sections, numbered clauses, and legal language."""
            },
            {
                "name": "HealthGuard_Medical_Necessity_Guidelines_2024.pdf",
                "type": "medical_necessity",
                "prompt": """Generate a medical necessity guidelines document for a health insurance company (2-3 pages).

Include:
- Definition of medical necessity
- Coverage criteria for common procedures
- Evidence-based guidelines
- Exclusions and limitations
- Documentation requirements
- Examples of medically necessary vs unnecessary services

Use specific medical terminology and cite clinical guidelines."""
            },
            {
                "name": "HealthGuard_Claims_Processing_Manual_2024.pdf",
                "type": "claims_processing",
                "prompt": """Generate a claims processing manual (2-3 pages).

Include:
- Claim submission requirements
- CPT and ICD code matching rules
- Timely filing limits (180 days from date of service)
- Duplicate claim detection
- Documentation requirements
- Common denial reasons and prevention
- Resubmission procedures

Be specific with timelines and requirements."""
            },
            {
                "name": "HealthGuard_Network_Coverage_Policy_2024.pdf",
                "type": "network_coverage",
                "prompt": """Generate a network coverage and out-of-network policy document (2 pages).

Include:
- In-network vs out-of-network coverage
- Emergency care exceptions
- Out-of-network claim procedures
- Coverage limitations
- Cost-sharing differences
- Provider verification requirements

Include specific percentage coverage rates."""
            },
            {
                "name": "HealthGuard_Appeals_Process_Guide_2024.pdf",
                "type": "appeals",
                "prompt": """Generate an appeals process guide for denied claims (2 pages).

Include:
- Appeals filing deadlines (60 days from denial)
- Required documentation
- Levels of appeal (first level, second level, external review)
- Timeframes for decisions
- Supporting evidence requirements
- Appeal letter format
- Contact information

Be specific about timelines and requirements."""
            }
        ]

        logger.info("Generating 5 policy documents...")

        generated_policies = []
        for policy in policies:
            logger.info(f"Generating: {policy['name']}")

            # Generate content with LLM
            content = await self._generate_document_content(policy['prompt'])

            # Create PDF
            pdf_path = self.policy_dir / policy['name']
            self._create_pdf(
                pdf_path,
                f"HealthGuard Insurance Company\n{policy['type'].replace('_', ' ').title()}",
                content
            )

            generated_policies.append({
                "name": policy['name'],
                "type": policy['type'],
                "path": str(pdf_path)
            })

            logger.info(f"✓ Created: {pdf_path}")

        return generated_policies

    async def generate_normal_denials(self) -> list[dict]:
        """Generate 5 normal claim denial scenarios."""

        denials = [
            {
                "name": "denial_001_duplicate_submission.pdf",
                "denial_reason": "duplicate_submission",
                "prompt": """Generate a claim denial letter for a DUPLICATE SUBMISSION.

Details:
- Patient: John Smith, DOB: 1985-03-15, Member ID: MEM123456789
- Provider: Dr. Sarah Johnson, NPI: 1234567890, City Medical Center
- Claim Number: CLM-2024-001234
- Service Date: 2024-01-15
- CPT Codes: 99213 (Office Visit), 85025 (Blood Count)
- Billed Amount: $245.00
- Denial Reason: This claim is a duplicate of claim CLM-2024-001100 already processed on 2024-01-20
- Denial Date: 2024-01-25
- Appeal Deadline: 60 days from denial date

Include standard denial letter format with payor contact information."""
            },
            {
                "name": "denial_002_cpt_mismatch.pdf",
                "denial_reason": "cpt_mismatch",
                "prompt": """Generate a claim denial letter for CPT CODE MISMATCH.

Details:
- Patient: Maria Garcia, DOB: 1972-08-22, Member ID: MEM987654321
- Provider: Dr. Michael Chen, NPI: 9876543210, Valley Health Clinic
- Claim Number: CLM-2024-002456
- Service Date: 2024-02-10
- CPT Codes: 99285 (Emergency Visit - High Complexity)
- ICD-10: J18.9 (Pneumonia)
- Billed Amount: $580.00
- Denial Reason: CPT code 99285 does not match the diagnosis code submitted. Medical record indicates routine office visit, not emergency department visit.
- Denial Date: 2024-02-18
- Appeal Deadline: 60 days

Use professional insurance company letterhead format."""
            },
            {
                "name": "denial_003_documentation_mismatch.pdf",
                "denial_reason": "documentation_mismatch",
                "prompt": """Generate a claim denial for INSUFFICIENT DOCUMENTATION.

Details:
- Patient: Robert Williams, DOB: 1960-11-30, Member ID: MEM456789123
- Provider: Dr. Emily Rodriguez, NPI: 4567891230, Premier Orthopedics
- Claim Number: CLM-2024-003789
- Service Date: 2024-03-05
- CPT Codes: 29881 (Knee Arthroscopy)
- ICD-10: M17.11 (Osteoarthritis of right knee)
- Billed Amount: $3,200.00
- Denial Reason: Submitted medical records do not support the medical necessity for surgical intervention. Conservative treatment documentation missing.
- Denial Date: 2024-03-15

Include specific documentation requirements."""
            },
            {
                "name": "denial_004_eligibility_cutoff.pdf",
                "denial_reason": "eligibility_cutoff",
                "prompt": """Generate a denial for PATIENT ELIGIBILITY ISSUE.

Details:
- Patient: Jennifer Lee, DOB: 1995-05-18, Member ID: MEM741852963
- Provider: Dr. James Park, NPI: 7418529630, Wellness Family Practice
- Claim Number: CLM-2024-004567
- Service Date: 2024-04-12
- CPT Codes: 99214 (Office Visit), 80053 (Metabolic Panel)
- Billed Amount: $185.00
- Denial Reason: Patient's coverage was terminated on 2024-04-01 due to non-payment of premiums. Patient was not eligible for coverage on date of service.
- Denial Date: 2024-04-20

Include member services contact information."""
            },
            {
                "name": "denial_005_prior_auth_missing.pdf",
                "denial_reason": "prior_authorization_missing",
                "prompt": """Generate a denial for MISSING PRIOR AUTHORIZATION.

Details:
- Patient: David Thompson, DOB: 1978-09-25, Member ID: MEM852963741
- Provider: Dr. Lisa Anderson, NPI: 8529637410, Advanced Imaging Center
- Claim Number: CLM-2024-005678
- Service Date: 2024-05-08
- CPT Codes: 72148 (MRI Lumbar Spine)
- ICD-10: M54.5 (Low back pain)
- Billed Amount: $1,450.00
- Denial Reason: Prior authorization required for MRI services per Policy Section 4.2.1. No authorization on file for date of service.
- Denial Date: 2024-05-15
- Appeal Deadline: 60 days

Note: Retrospective authorization may be requested with supporting documentation."""
            }
        ]

        logger.info("Generating 5 normal denial letters...")

        generated_denials = []
        for denial in denials:
            logger.info(f"Generating: {denial['name']}")

            content = await self._generate_document_content(denial['prompt'])

            pdf_path = self.test_cases_dir / "synthetic" / denial['name']
            self._create_pdf(pdf_path, "CLAIM DENIAL NOTICE", content)

            generated_denials.append({
                "name": denial['name'],
                "denial_reason": denial['denial_reason'],
                "path": str(pdf_path),
                "category": "normal"
            })

            logger.info(f"✓ Created: {pdf_path}")

        return generated_denials

    async def generate_edge_case_denials(self) -> list[dict]:
        """Generate 5 edge case denials."""

        edge_cases = [
            {
                "name": "denial_edge_001_poor_scan_quality.pdf",
                "scenario": "poor_scan",
                "prompt": """Generate a claim denial letter but format it as if it was poorly scanned/copied.

Include:
- Faded text sections
- Extra header/footer noise: "SCANNED BY MEDITECH 3000" "PAGE 1 OF 2" "CONFIDENTIAL"
- Some sections with irregular spacing
- Watermark text: "COPY - NOT FOR OFFICIAL USE"
- Patient: Thomas Martinez (partial info visible)
- Claim for Emergency Room visit denied for documentation issues

Make it look like a low-quality photocopy with artifacts."""
            },
            {
                "name": "denial_edge_002_bilingual.pdf",
                "scenario": "bilingual",
                "prompt": """Generate a claim denial letter that mixes English and Spanish.

Details:
- Patient: Ana Rodriguez/Ana Rodríguez
- Some sections in Spanish: "Razón de Negación", "Fecha de Servicio"
- Other sections in English: "Claim Number", "Appeal Rights"
- Include accented characters: é, á, í, ñ
- Mix both languages naturally as might occur in bilingual healthcare setting

Claim denied for missing prior authorization for specialist visit."""
            },
            {
                "name": "denial_edge_003_multiple_patients.pdf",
                "scenario": "multiple_patients",
                "prompt": """Generate a denial notice that lists MULTIPLE PATIENTS on one page (billing office batch format).

Include:
- Header: "Batch Denial Summary - Provider Group: City Medical Associates"
- List 3 patients with claim details:
  1. Patient A - Duplicate claim
  2. Patient B - Authorization missing (TARGET FOR EXTRACTION)
  3. Patient C - Eligibility issue
- Each has partial info (name, member ID, date, denial reason)
- Make it ambiguous which patient is primary

Test ability to extract correct patient when multiple are present."""
            },
            {
                "name": "denial_edge_004_truncated.pdf",
                "scenario": "truncated",
                "prompt": """Generate a claim denial letter that appears INCOMPLETE/TRUNCATED.

Details:
- Start with normal denial letter
- Include: Patient name, claim number, service date
- Denial reason starts but cuts off mid-sentence: "This claim is denied because the submitted documentation does not demonstrate medical neces..."
- Missing signature block
- No appeal instructions
- Page indicator: "Page 1 of 2" but only page 1 provided
- Footer: "Continued on next page..."

Test handling of incomplete information."""
            },
            {
                "name": "denial_edge_005_extraneous_headers.pdf",
                "scenario": "extraneous_headers",
                "prompt": """Generate a denial letter with EXCESSIVE HEADERS/FOOTERS.

Include:
- Top header: Company logo text, "HealthGuard Insurance - Claims Department", date/time stamp
- Page headers: "CONFIDENTIAL PATIENT INFORMATION - DO NOT DISTRIBUTE"
- Footers: "Page 1 of 1 | Printed: 2024-05-15 14:23:45 | User: CLAIMS_ADM | Document ID: DEN2024051545"
- Watermark: "OFFICIAL DENIAL NOTICE - RETAIN FOR RECORDS"
- Side margins with: "INTERNAL USE ONLY"
- Actual claim info buried in middle

Test extraction from noisy documents with extra metadata."""
            }
        ]

        logger.info("Generating 5 edge case denials...")

        generated = []
        for case in edge_cases:
            logger.info(f"Generating: {case['name']}")

            content = await self._generate_document_content(case['prompt'])

            pdf_path = self.test_cases_dir / "edge_cases" / case['name']
            self._create_pdf(pdf_path, "EDGE CASE DENIAL", content)

            generated.append({
                "name": case['name'],
                "scenario": case['scenario'],
                "path": str(pdf_path),
                "category": "edge_case"
            })

            logger.info(f"✓ Created: {pdf_path}")

        return generated

    async def _generate_document_content(self, prompt: str) -> str:
        """Generate document content using LLM."""

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at creating realistic healthcare insurance documents. Generate detailed, professional content."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        return response.choices[0].message.content

    def _create_pdf(self, filepath: Path, title: str, content: str):
        """Create a PDF document from text content."""

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor='darkblue',
            spaceAfter=30,
            alignment=TA_LEFT
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )

        # Build content
        story = []

        # Title
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))

        # Body paragraphs
        for para in content.split('\n\n'):
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
                story.append(Spacer(1, 0.1*inch))

        # Build PDF
        doc.build(story)


async def main():
    """Main data generation function."""

    logger.info("=" * 60)
    logger.info("SYNTHETIC DATA GENERATION")
    logger.info("=" * 60)
    logger.info("")

    generator = SyntheticDataGenerator()

    # Generate policy documents
    logger.info("Step 1: Generating Policy Documents")
    logger.info("-" * 60)
    policies = await generator.generate_policy_documents()
    logger.info(f"✓ Generated {len(policies)} policy documents")
    logger.info("")

    # Generate normal denials
    logger.info("Step 2: Generating Normal Denials")
    logger.info("-" * 60)
    normal_denials = await generator.generate_normal_denials()
    logger.info(f"✓ Generated {len(normal_denials)} normal denials")
    logger.info("")

    # Generate edge cases
    logger.info("Step 3: Generating Edge Case Denials")
    logger.info("-" * 60)
    edge_denials = await generator.generate_edge_case_denials()
    logger.info(f"✓ Generated {len(edge_denials)} edge case denials")
    logger.info("")

    # Save manifest
    manifest = {
        "policies": policies,
        "normal_denials": normal_denials,
        "edge_case_denials": edge_denials,
        "generated_at": "2024-01-15T10:00:00Z"
    }

    manifest_path = Path("data/test_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Total documents generated: {len(policies) + len(normal_denials) + len(edge_denials)}")
    logger.info(f"Manifest saved to: {manifest_path}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Generate adversarial test cases: python scripts/generate_adversarial_cases.py")
    logger.info("2. Index policy documents: python scripts/index_policies.py")
    logger.info("3. Run tests: pytest tests/")


if __name__ == "__main__":
    asyncio.run(main())
