"""
Test a single claim to see system outputs.
Shows extraction, policy retrieval, reasoning, and citation verification.
"""

import asyncio
from pathlib import Path
import json
from openai import AsyncOpenAI
import os
import chromadb

async def test_single_claim():
    """Test processing a single claim denial."""

    print("=" * 80)
    print("CLAIM TRIAGE SYSTEM - SINGLE CLAIM TEST")
    print("=" * 80)
    print()

    # Initialize OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path="data/vector_store")
    collection = chroma_client.get_collection(name="policy_documents")

    # Test with first denial PDF
    pdf_path = Path("data/test_cases/synthetic/denial_001_duplicate.pdf")

    print(f"📄 Processing: {pdf_path.name}")
    print("-" * 80)
    print()

    # Step 1: Extract text from PDF (simple extraction)
    print("🔍 STEP 1: EXTRACTING CLAIM DATA FROM PDF")
    print("-" * 80)

    # Read PDF using PyMuPDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        pdf_text = ""
        for page in doc:
            pdf_text += page.get_text()
        doc.close()

        print(f"✓ Extracted {len(pdf_text)} characters from PDF")
        print(f"\nFirst 500 characters:")
        print(pdf_text[:500])
        print("...\n")

    except Exception as e:
        print(f"✗ Error reading PDF: {e}")
        return

    # Step 2: Use OpenAI to extract structured data
    print("\n🤖 STEP 2: EXTRACTING STRUCTURED DATA WITH GPT-4o")
    print("-" * 80)

    extraction_prompt = f"""Extract the following information from this claim denial letter:

PDF Content:
{pdf_text}

Extract:
1. Claim Number
2. Patient Name
3. Member ID
4. Service Date
5. Denial Reason (brief)
6. Billed Amount
7. Provider NPI

Return as JSON with keys: claim_number, patient_name, member_id, service_date, denial_reason, billed_amount, provider_npi, confidence_score (0-1)
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a medical claims data extraction expert. Extract data accurately and return valid JSON."},
            {"role": "user", "content": extraction_prompt}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    extracted_data = json.loads(response.choices[0].message.content)

    print("✓ Extraction Complete:")
    for key, value in extracted_data.items():
        print(f"  • {key}: {value}")
    print()

    # Step 3: Retrieve relevant policies
    print("\n📚 STEP 3: RETRIEVING RELEVANT POLICIES")
    print("-" * 80)

    denial_reason = extracted_data.get('denial_reason', 'Unknown')
    query = f"Policy regarding {denial_reason} in healthcare claims"

    print(f"Query: '{query}'")
    print()

    # Generate embedding for query
    embedding_response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = embedding_response.data[0].embedding

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    print(f"✓ Found {len(results['documents'][0])} relevant policy sections:")
    print()

    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        similarity = 1 - distance  # Convert distance to similarity
        print(f"  [{i}] Policy: {metadata['policy_name']}")
        print(f"      Similarity: {similarity:.2%}")
        print(f"      Content: {doc[:150]}...")
        print()

    # Step 4: Reason about appealability
    print("\n🧠 STEP 4: REASONING ABOUT APPEALABILITY")
    print("-" * 80)

    reasoning_prompt = f"""Based on this claim denial and relevant policies, determine if this should be appealed.

Claim Information:
{json.dumps(extracted_data, indent=2)}

Relevant Policies:
{chr(10).join([f"Policy {i+1}: {doc}" for i, doc in enumerate(results['documents'][0])])}

Analyze:
1. Should this claim be appealed? (yes/no)
2. Why or why not?
3. What policy sections support your reasoning?
4. Confidence in your decision (0-1)

Return as JSON with keys: should_appeal (boolean), reasoning (string), policy_references (list), confidence_score (float)
"""

    reasoning_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a healthcare appeals specialist. Analyze claims and determine appealability based on policy."},
            {"role": "user", "content": reasoning_prompt}
        ],
        temperature=0.0,
        max_tokens=4096,
        response_format={"type": "json_object"}
    )

    reasoning_data = json.loads(reasoning_response.choices[0].message.content)

    print("✓ Reasoning Complete:")
    print(f"  • Should Appeal: {reasoning_data.get('should_appeal')}")
    print(f"  • Confidence: {reasoning_data.get('confidence_score', 0):.2%}")
    print(f"  • Reasoning: {reasoning_data.get('reasoning', '')[:200]}...")
    print(f"  • Policy References: {', '.join(reasoning_data.get('policy_references', []))}")
    print()

    # Step 5: Generate appeal draft (if appealable)
    if reasoning_data.get('should_appeal'):
        print("\n📝 STEP 5: GENERATING APPEAL DRAFT")
        print("-" * 80)

        appeal_prompt = f"""Generate a professional appeal letter for this claim denial.

Claim Information:
{json.dumps(extracted_data, indent=2)}

Reasoning:
{reasoning_data.get('reasoning')}

Policy Support:
{chr(10).join([f"- {doc[:200]}" for doc in results['documents'][0]])}

Generate a formal appeal letter with:
1. Professional header
2. Clear statement of appeal
3. Policy citations supporting the appeal
4. Request for reconsideration
5. Professional closing

Format as a complete appeal letter.
"""

        appeal_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional medical appeals writer. Write clear, policy-based appeal letters."},
                {"role": "user", "content": appeal_prompt}
            ],
            temperature=0.0,
            max_tokens=4096
        )

        appeal_draft = appeal_response.choices[0].message.content

        print("✓ Appeal Draft Generated:")
        print()
        print(appeal_draft[:800])
        print("\n... (truncated)")
        print()

    # Summary
    print("\n" + "=" * 80)
    print("✅ PROCESSING COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Claim: {extracted_data.get('claim_number', 'N/A')}")
    print(f"  • Patient: {extracted_data.get('patient_name', 'N/A')}")
    print(f"  • Denial Reason: {extracted_data.get('denial_reason', 'N/A')}")
    print(f"  • Extraction Confidence: {extracted_data.get('confidence_score', 0):.2%}")
    print(f"  • Should Appeal: {reasoning_data.get('should_appeal', False)}")
    print(f"  • Reasoning Confidence: {reasoning_data.get('confidence_score', 0):.2%}")
    print(f"  • Policies Retrieved: {len(results['documents'][0])}")
    print()

    if reasoning_data.get('should_appeal'):
        print("✓ Appeal letter generated and ready for review")
    else:
        print("✗ Appeal not recommended based on policy analysis")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_single_claim())
