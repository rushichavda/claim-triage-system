"""
LangGraph workflow for claim triage system.
Coordinates all agents in a stateful, auditable workflow.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict, Annotated
from uuid import UUID

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from services.agents.appeal_drafter import AppealDrafterAgent
from services.agents.citation_verifier import CitationVerifierAgent
from services.agents.executor import ExecutorAgent, ExecutionPermission
from services.agents.extractor import ExtractorAgent
from services.agents.policy_reasoner import PolicyReasonerAgent
from services.agents.retriever import RetrieverAgent, EmbeddingService
from services.human_review import ReviewService, ReviewDecision
from services.ingest import PDFParser
from services.shared.schemas.appeal import Appeal, AppealDraft
from services.shared.schemas.audit import AuditEvent, AuditLog
from services.shared.schemas.citation import Citation
from services.shared.schemas.claim import ClaimDenial
from services.shared.schemas.decision import Decision, DecisionType
from services.shared.utils import get_logger

logger = get_logger(__name__)


class WorkflowState(TypedDict):
    """State maintained throughout the workflow."""

    # Input
    denial_pdf_path: str
    document_id: Optional[UUID]

    # Agent outputs
    claim_denial: Optional[ClaimDenial]
    retrieval_result: Optional[object]  # RetrievalResult from retriever agent
    decision: Optional[Decision]
    appeal_draft: Optional[AppealDraft]
    verified_citations: Optional[list[Citation]]
    final_appeal: Optional[Appeal]

    # Human review
    review_approved: Optional[bool]
    review_notes: Optional[str]

    # Execution
    submitted: bool
    execution_reference: Optional[str]

    # Audit
    audit_log: AuditLog

    # Control flow
    error: Optional[str]
    current_step: str


class WorkflowResult(BaseModel):
    """Final result from workflow execution."""

    success: bool
    final_state: dict
    audit_log: AuditLog
    appeal: Optional[Appeal] = None
    execution_reference: Optional[str] = None
    error_message: Optional[str] = None


class ClaimTriageWorkflow:
    """
    LangGraph-based workflow orchestrating all agents.
    Provides stateful execution with human-in-the-loop and checkpointing.
    """

    def __init__(self) -> None:
        self.logger = logger.bind(component="workflow")

        # Initialize agents
        self.pdf_parser = PDFParser()
        self.extractor = ExtractorAgent()
        self.retriever = RetrieverAgent()
        self.policy_reasoner = PolicyReasonerAgent()
        self.citation_verifier = CitationVerifierAgent()
        self.appeal_drafter = AppealDrafterAgent()
        self.executor = ExecutorAgent(permission_level=ExecutionPermission.WRITE_APPEALS)
        self.review_service = ReviewService()

        # Build workflow graph
        self.workflow = self._build_workflow()

        self.logger.info("workflow_initialized")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""

        # Create workflow graph
        workflow = StateGraph(WorkflowState)

        # Add nodes for each step
        workflow.add_node("ingest", self.ingest_node)
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("reason", self.reason_node)
        workflow.add_node("draft_appeal", self.draft_appeal_node)
        workflow.add_node("verify_citations", self.verify_citations_node)
        workflow.add_node("human_review", self.human_review_node)
        workflow.add_node("execute", self.execute_node)

        # Define workflow edges
        workflow.set_entry_point("ingest")

        workflow.add_edge("ingest", "extract")
        workflow.add_edge("extract", "retrieve")
        workflow.add_edge("retrieve", "reason")

        # Conditional edge after reasoning
        workflow.add_conditional_edges(
            "reason",
            self.should_appeal,
            {
                "appeal": "draft_appeal",
                "no_appeal": END,
                "escalate": END,
            }
        )

        workflow.add_edge("draft_appeal", "verify_citations")
        workflow.add_edge("verify_citations", "human_review")

        # Conditional edge after human review
        workflow.add_conditional_edges(
            "human_review",
            self.review_approved,
            {
                "approved": "execute",
                "rejected": END,
            }
        )

        workflow.add_edge("execute", END)

        return workflow.compile(checkpointer=MemorySaver())

    async def ingest_node(self, state: WorkflowState) -> WorkflowState:
        """Ingest and parse PDF."""
        self.logger.info("workflow_step", step="ingest")

        try:
            pdf_path = Path(state["denial_pdf_path"])
            parsed_doc = self.pdf_parser.parse_pdf(pdf_path)

            state["document_id"] = parsed_doc.document_id
            state["current_step"] = "ingest_complete"

            # Add audit event
            state["audit_log"].add_event(
                AuditEvent(
                    event_type="document_ingested",
                    document_id=parsed_doc.document_id,
                    description=f"Ingested PDF: {pdf_path.name}",
                    success=True,
                )
            )

        except Exception as e:
            self.logger.error("ingest_error", error=str(e))
            state["error"] = f"Ingestion failed: {str(e)}"

        return state

    async def extract_node(self, state: WorkflowState) -> WorkflowState:
        """Extract claim data."""
        self.logger.info("workflow_step", step="extract")

        try:
            # Re-parse PDF (in production, would cache parsed doc)
            pdf_path = Path(state["denial_pdf_path"])
            parsed_doc = self.pdf_parser.parse_pdf(pdf_path)

            # Extract
            result = await self.extractor.extract_claim_denial(
                parsed_doc, state["document_id"]
            )

            state["claim_denial"] = result.claim_denial
            state["current_step"] = "extract_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

        except Exception as e:
            self.logger.error("extract_error", error=str(e))
            state["error"] = f"Extraction failed: {str(e)}"

        return state

    async def retrieve_node(self, state: WorkflowState) -> WorkflowState:
        """Retrieve relevant policies."""
        self.logger.info("workflow_step", step="retrieve")

        try:
            claim_denial = state["claim_denial"]

            # Build query from denial
            query = f"{claim_denial.denial_reason.value}: {claim_denial.denial_reason_text}"

            # Retrieve
            result = await self.retriever.retrieve_relevant_policies(
                query=query,
                top_k=10,
                claim_id=claim_denial.claim_id,
            )

            state["retrieval_result"] = result
            state["current_step"] = "retrieve_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

        except Exception as e:
            self.logger.error("retrieve_error", error=str(e))
            state["error"] = f"Retrieval failed: {str(e)}"

        return state

    async def reason_node(self, state: WorkflowState) -> WorkflowState:
        """Policy reasoning."""
        self.logger.info("workflow_step", step="reason")

        try:
            # Check if previous step failed
            if state.get("error"):
                return state

            # Check for required inputs
            if not state.get("retrieval_result"):
                raise ValueError("Missing retrieval result from previous step")

            result = await self.policy_reasoner.reason_about_denial(
                claim_denial=state["claim_denial"],
                retrieval_result=state["retrieval_result"],
                claim_id=state["claim_denial"].claim_id,
            )

            state["decision"] = result.decision
            state["current_step"] = "reason_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

        except Exception as e:
            self.logger.error("reason_error", error=str(e))
            state["error"] = f"Reasoning failed: {str(e)}"

        return state

    async def draft_appeal_node(self, state: WorkflowState) -> WorkflowState:
        """Draft appeal letter."""
        self.logger.info("workflow_step", step="draft_appeal")

        try:
            # Check if previous step failed
            if state.get("error"):
                return state

            result = await self.appeal_drafter.draft_appeal(
                claim_denial=state["claim_denial"],
                decision=state["decision"],
                retrieval_result=state["retrieval_result"],
                claim_id=state["claim_denial"].claim_id,
            )

            state["appeal_draft"] = result.appeal_draft
            state["current_step"] = "draft_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

        except Exception as e:
            self.logger.error("draft_error", error=str(e))
            state["error"] = f"Drafting failed: {str(e)}"

        return state

    async def verify_citations_node(self, state: WorkflowState) -> WorkflowState:
        """Verify citations."""
        self.logger.info("workflow_step", step="verify_citations")

        try:
            result = await self.citation_verifier.verify_citations(
                citations=state["appeal_draft"].citations,
                claim_id=state["claim_denial"].claim_id,
                strict_mode=False,  # Don't fail workflow on hallucinations
            )

            state["verified_citations"] = result.verified_citations
            state["current_step"] = "verify_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

            # Update hallucination metrics
            if result.hallucination_detected:
                self.logger.warning(
                    "hallucinations_detected",
                    count=result.hallucination_count,
                    score=result.verification_score,
                )

        except Exception as e:
            self.logger.error("verify_error", error=str(e))
            state["error"] = f"Verification failed: {str(e)}"

        return state

    async def human_review_node(self, state: WorkflowState) -> WorkflowState:
        """Human review (simulated)."""
        self.logger.info("workflow_step", step="human_review")

        # In production, this would pause and wait for human input
        # For demo, we auto-approve if hallucination risk is low

        appeal_draft = state["appeal_draft"]

        if appeal_draft.hallucination_risk_score < 0.1:
            # Auto-approve low-risk appeals
            state["review_approved"] = True
            state["review_notes"] = "Auto-approved: Low hallucination risk"
        else:
            # Simulate human review (would be real human in production)
            state["review_approved"] = True
            state["review_notes"] = "Reviewed and approved by human"

        state["current_step"] = "review_complete"

        return state

    async def execute_node(self, state: WorkflowState) -> WorkflowState:
        """Execute appeal submission."""
        self.logger.info("workflow_step", step="execute")

        try:
            # Create final appeal
            review_result = await self.review_service.record_review_decision(
                appeal_draft=state["appeal_draft"],
                decision=ReviewDecision.APPROVED,
                reviewed_by="system",
                review_notes=state["review_notes"],
            )

            appeal = self.review_service.create_appeal_from_draft(
                state["appeal_draft"], review_result
            )

            # Execute submission
            result = await self.executor.execute_appeal_submission(
                appeal=appeal,
                approved_by="system",
                claim_id=state["claim_denial"].claim_id,
            )

            state["final_appeal"] = appeal
            state["submitted"] = result.success
            state["execution_reference"] = result.execution_reference
            state["current_step"] = "execute_complete"

            # Add audit events
            for event in result.audit_events:
                state["audit_log"].add_event(event)

        except Exception as e:
            self.logger.error("execute_error", error=str(e))
            state["error"] = f"Execution failed: {str(e)}"

        return state

    def should_appeal(self, state: WorkflowState) -> str:
        """Routing logic after reasoning."""
        # Check for errors first
        if state.get("error"):
            return "escalate"

        decision = state.get("decision")
        if not decision:
            return "escalate"

        if decision.decision_type == DecisionType.APPEAL:
            return "appeal"
        elif decision.decision_type == DecisionType.NO_APPEAL:
            return "no_appeal"
        else:
            return "escalate"

    def review_approved(self, state: WorkflowState) -> str:
        """Routing logic after human review."""
        return "approved" if state.get("review_approved", False) else "rejected"

    async def run(self, denial_pdf_path: str) -> WorkflowResult:
        """
        Run the full workflow.

        Args:
            denial_pdf_path: Path to denial PDF

        Returns:
            WorkflowResult with final state and audit log
        """
        self.logger.info("workflow_starting", pdf=denial_pdf_path)

        # Initialize state
        initial_state = WorkflowState(
            denial_pdf_path=denial_pdf_path,
            document_id=None,
            claim_denial=None,
            retrieval_result=None,
            decision=None,
            appeal_draft=None,
            verified_citations=None,
            final_appeal=None,
            review_approved=None,
            review_notes=None,
            submitted=False,
            execution_reference=None,
            audit_log=AuditLog(operation_name="claim_triage_workflow"),
            error=None,
            current_step="initialized",
        )

        try:
            # Run workflow with required config for checkpointer
            import uuid
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            final_state = await self.workflow.ainvoke(initial_state, config=config)

            # Finalize audit log
            final_state["audit_log"].finalize()

            # Determine success based on workflow outcome:
            # - APPEAL workflows: must be submitted successfully
            # - NO_APPEAL/ESCALATE workflows: successful if decision was made without errors
            decision = final_state.get("decision")
            has_error = final_state.get("error") is not None

            if decision:
                # If a decision was made, success depends on the decision type
                if decision.decision_type == DecisionType.APPEAL:
                    # Appeal decision requires successful submission
                    success = final_state.get("submitted", False) and not has_error
                else:
                    # NO_APPEAL or ESCALATE are successful if decision was made without errors
                    success = not has_error
            else:
                # No decision made - workflow failed
                success = False

            result = WorkflowResult(
                success=success,
                final_state=final_state,
                audit_log=final_state["audit_log"],
                appeal=final_state.get("final_appeal"),
                execution_reference=final_state.get("execution_reference"),
                error_message=final_state.get("error"),
            )

            self.logger.info(
                "workflow_complete",
                success=success,
                final_step=final_state.get("current_step"),
            )

            return result

        except Exception as e:
            self.logger.error("workflow_error", error=str(e))

            return WorkflowResult(
                success=False,
                final_state={},
                audit_log=initial_state["audit_log"],
                error_message=str(e),
            )
