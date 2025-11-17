"""
Unit tests for Retriever Agent.
Tests semantic search and policy document retrieval.
"""

import pytest
from uuid import uuid4
from pathlib import Path

from services.agents.retriever.retriever_agent import RetrieverAgent
from services.shared.schemas.policy import PolicyDocument, PolicyChunk
from services.shared.schemas.claim import ClaimDenial, DenialReason


@pytest.fixture
def retriever_agent():
    """Create RetrieverAgent instance."""
    return RetrieverAgent()


@pytest.fixture
def sample_policy_doc():
    """Create sample policy document."""
    return PolicyDocument(
        policy_id=uuid4(),
        policy_name="prior_authorization_policy",
        policy_type="prior_authorization",
        content="""
SECTION 4.2.1 - EMERGENCY EXCEPTION:
Prior authorization is WAIVED for emergency services within 24 hours of ED admission.

SECTION 5.3 - SERVICES REQUIRING AUTH:
- MRI/CT scans (except emergencies)
- Surgeries over $5,000
- Specialty consults
        """,
        source_file="data/policy_docs/prior_authorization_policy.txt",
        effective_date="2024-01-01",
        version="1.0"
    )


@pytest.fixture
def sample_claim():
    """Create sample claim denial."""
    return ClaimDenial(
        claim_id=uuid4(),
        denial_id=uuid4(),
        denial_reason=DenialReason.PRIOR_AUTHORIZATION_MISSING,
        denial_reason_text="Prior authorization required for MRI services",
        patient_name="John Doe",
        member_id="MEM123456789",
        confidence_score=0.90
    )


class TestRetrieverAgent:
    """Unit tests for Retriever Agent."""

    @pytest.mark.asyncio
    async def test_index_policy_document(self, retriever_agent, sample_policy_doc):
        """Test indexing a policy document into vector store."""
        # Create simple chunks
        chunks = [
            PolicyChunk(
                chunk_id=uuid4(),
                policy_id=sample_policy_doc.policy_id,
                chunk_index=0,
                content="Prior authorization is WAIVED for emergency services within 24 hours of ED admission",
                start_byte=0,
                end_byte=100,
                policy_type="prior_authorization"
            )
        ]

        result = await retriever_agent.index_policy_document(sample_policy_doc, chunks)

        assert result is True or result is None  # Successful indexing

    @pytest.mark.asyncio
    async def test_retrieve_relevant_policies(self, retriever_agent, sample_claim):
        """Test retrieval of relevant policies for a claim."""
        # Note: Requires policies to be indexed first
        results = await retriever_agent.retrieve(sample_claim, top_k=5)

        assert results is not None
        assert isinstance(results, list)
        # Should return policy chunks
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_retrieve_with_query_text(self, retriever_agent):
        """Test retrieval using query text."""
        query = "What are the requirements for prior authorization for MRI scans?"

        results = await retriever_agent.retrieve_by_query(query, top_k=3)

        assert results is not None
        assert isinstance(results, list)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_semantic_search_relevance(self, retriever_agent):
        """Test that semantic search returns relevant results."""
        # Query about emergency exceptions
        query = "When is prior authorization waived for emergency services?"

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        # Should return results
        assert len(results) > 0

        # Results should have relevance scores
        for result in results:
            if hasattr(result, 'relevance_score'):
                assert result.relevance_score >= 0.0
                assert result.relevance_score <= 1.0

    @pytest.mark.asyncio
    async def test_retrieve_by_policy_type(self, retriever_agent):
        """Test filtering retrieval by policy type."""
        query = "prior authorization requirements"

        results = await retriever_agent.retrieve_by_query(
            query,
            top_k=5,
            policy_type="prior_authorization"
        )

        assert results is not None
        # Results should be filtered to specific policy type
        for result in results:
            if hasattr(result, 'policy_type'):
                assert result.policy_type == "prior_authorization"

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, retriever_agent):
        """Test handling of empty query."""
        results = await retriever_agent.retrieve_by_query("", top_k=5)

        # Should handle gracefully
        assert results is not None
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_top_k_limit(self, retriever_agent):
        """Test that top_k parameter limits results."""
        query = "authorization requirements"

        results_3 = await retriever_agent.retrieve_by_query(query, top_k=3)
        results_10 = await retriever_agent.retrieve_by_query(query, top_k=10)

        assert len(results_3) <= 3
        assert len(results_10) <= 10


class TestRetrieverAgentEmbeddings:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self, retriever_agent):
        """Test embedding generation for text."""
        text = "Prior authorization is required for MRI scans"

        embedding = await retriever_agent.generate_embedding(text)

        assert embedding is not None
        assert isinstance(embedding, (list, tuple))
        assert len(embedding) > 0
        # Qwen3-Embedding-0.6B produces 768-dim embeddings
        assert len(embedding) == 768 or len(embedding) > 500

    @pytest.mark.asyncio
    async def test_embedding_consistency(self, retriever_agent):
        """Test that same text produces same embedding."""
        text = "Prior authorization is required"

        embedding1 = await retriever_agent.generate_embedding(text)
        embedding2 = await retriever_agent.generate_embedding(text)

        # Should be identical or very similar
        import numpy as np
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

        assert similarity > 0.99  # Almost identical

    @pytest.mark.asyncio
    async def test_semantic_similarity_different_wording(self, retriever_agent):
        """Test semantic similarity for same meaning, different wording."""
        text1 = "Prior authorization is required for MRI scans"
        text2 = "MRI scans need pre-approval"

        embedding1 = await retriever_agent.generate_embedding(text1)
        embedding2 = await retriever_agent.generate_embedding(text2)

        import numpy as np
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

        # Should be semantically similar
        assert similarity > 0.70


class TestRetrieverAgentIntegration:
    """Integration tests with policy documents."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not Path("data/policy_docs").exists(), reason="Policy docs not found")
    async def test_retrieve_from_indexed_policies(self, retriever_agent):
        """Test retrieval from actual indexed policy documents."""
        # This assumes policies have been indexed
        query = "What are the requirements for prior authorization?"

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        assert results is not None
        assert len(results) > 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(not Path("data/policy_docs").exists(), reason="Policy docs not found")
    async def test_retrieve_emergency_exception(self, retriever_agent):
        """Test retrieval of emergency exception policy."""
        query = "When is prior authorization waived for emergency services?"

        results = await retriever_agent.retrieve_by_query(query, top_k=3)

        assert len(results) > 0

        # Should contain relevant policy text
        combined_text = " ".join([r.content for r in results if hasattr(r, 'content')])
        assert "emergency" in combined_text.lower() or "waived" in combined_text.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not Path("data/policy_docs").exists(), reason="Policy docs not found")
    async def test_retrieve_medical_necessity(self, retriever_agent):
        """Test retrieval of medical necessity guidelines."""
        query = "What are the medical necessity requirements for knee arthroscopy?"

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        assert len(results) > 0


@pytest.mark.integration
class TestRetrieverAgentPerformance:
    """Performance tests for retrieval."""

    @pytest.mark.asyncio
    async def test_retrieval_speed(self, retriever_agent):
        """Test that retrieval completes within reasonable time."""
        import time

        query = "prior authorization requirements"

        start = time.time()
        results = await retriever_agent.retrieve_by_query(query, top_k=10)
        duration = time.time() - start

        assert results is not None
        # Should complete within 3 seconds
        assert duration < 3.0

    @pytest.mark.asyncio
    async def test_batch_retrieval_performance(self, retriever_agent):
        """Test batch retrieval performance."""
        import time
        import asyncio

        queries = [
            "prior authorization requirements",
            "emergency exception policy",
            "medical necessity guidelines",
            "appeals process",
            "network coverage rules"
        ]

        start = time.time()
        results = await asyncio.gather(*[
            retriever_agent.retrieve_by_query(q, top_k=5) for q in queries
        ])
        duration = time.time() - start

        assert len(results) == 5
        # Should complete batch within 10 seconds
        assert duration < 10.0

    @pytest.mark.asyncio
    async def test_embedding_generation_speed(self, retriever_agent):
        """Test embedding generation performance."""
        import time

        text = "Prior authorization is required for MRI scans and CT scans except in emergency situations"

        start = time.time()
        embedding = await retriever_agent.generate_embedding(text)
        duration = time.time() - start

        assert embedding is not None
        # Should complete within 1 second
        assert duration < 1.0


class TestRetrieverAgentEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_retrieve_with_very_long_query(self, retriever_agent):
        """Test retrieval with very long query text."""
        # Create long query
        query = "prior authorization " * 100  # Very long repeated text

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        # Should handle gracefully
        assert results is not None
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_with_special_characters(self, retriever_agent):
        """Test retrieval with special characters in query."""
        query = "prior authorization @#$% requirements <test>"

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        # Should handle gracefully
        assert results is not None

    @pytest.mark.asyncio
    async def test_retrieve_with_non_ascii_characters(self, retriever_agent):
        """Test retrieval with non-ASCII characters."""
        query = "autorización previa requerida"  # Spanish

        results = await retriever_agent.retrieve_by_query(query, top_k=5)

        # Should handle non-ASCII
        assert results is not None
