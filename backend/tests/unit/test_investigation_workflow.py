from app.agents.workflow import InvestigationWorkflow
from app.llm import LLMCompletion, LLMError
from app.synthetic_data import build_incidents


def test_investigation_workflow_builds_an_evidence_based_summary() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    incident = build_incidents()[0]

    report = workflow.analyze_incident(incident.incident_id)

    assert report["incident_id"] == incident.incident_id
    assert report["service"] == incident.service
    assert len(report["evidence_documents"]) > 0
    assert report["candidate_root_cause"]
    assert report["confidence"] >= 0.0


def test_investigation_workflow_populates_a_reasoning_summary() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    report = workflow.analyze_incident("INC-001")

    assert "root cause" in report["summary"].lower()
    assert "evidence" in report["summary"].lower()


def test_investigation_workflow_collects_runtime_evidence() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    report = workflow.analyze_incident("INC-001")

    assert "tool_findings" in report
    assert report["tool_findings"]["deployment"]["service"] == "checkout-api"
    assert report["tool_findings"]["logs"]["error_count"] >= 1
    assert report["tool_findings"]["metrics"]["service"] == "checkout-api"


def test_investigation_workflow_runs_a_langgraph_orchestration() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    report = workflow.analyze_incident("INC-001")

    assert "graph_path" in report
    assert report["graph_path"][0] == "retrieve_documents"
    assert report["graph_path"][-1] == "synthesize_summary"


def test_investigation_workflow_requires_human_approval() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    report = workflow.analyze_incident("INC-001")

    assert "recommendation" in report
    assert report["recommendation"]["requires_human_approval"] is True
    assert report["recommendation"]["approval_status"] == "pending"


def test_investigation_workflow_tracks_remediation_timeline() -> None:
    workflow = InvestigationWorkflow(use_configured_llm=False)
    report = workflow.analyze_incident("INC-001")

    assert "timeline" in report
    assert report["timeline"][0]["event"] == "incident_received"
    assert report["timeline"][-1]["event"] == "recommendation_ready"


def test_llm_synthesis_uses_only_incident_and_retrieved_evidence() -> None:
    class StubLLM:
        def __init__(self) -> None:
            self.messages = []

        def complete(self, messages):
            self.messages = messages
            return LLMCompletion(
                content={
                    "candidate_root_cause": "Possible database saturation after a deployment.",
                    "summary": "Runtime errors and retrieved documents support this hypothesis.",
                    "recommended_action": "Validate the connection settings, then consider a human-approved rollback.",
                },
                provider="groq",
                model="test-model",
            )

    llm = StubLLM()
    report = InvestigationWorkflow(llm_client=llm).analyze_incident("INC-001")
    prompt = " ".join(str(message.get("content", "")) for message in llm.messages)

    assert report["llm"] == {
        "mode": "llm",
        "provider": "groq",
        "model": "test-model",
        "reason": None,
    }
    assert report["confidence"] is None
    assert report["recommendation"]["recommended_action"].startswith("Validate the connection")
    assert "ground_truth_root_cause" not in prompt
    assert "expected_evidence" not in prompt


def test_llm_failure_uses_evidence_only_fallback() -> None:
    class FailedLLM:
        def complete(self, messages):
            raise LLMError("provider unavailable", code="provider_connection")

    report = InvestigationWorkflow(llm_client=FailedLLM()).analyze_incident("INC-001")

    assert report["llm"]["mode"] == "deterministic_fallback"
    assert report["llm"]["reason"] == "provider_connection"
    assert report["confidence_basis"] == "heuristic_evidence_coverage_not_calibrated_probability"
    assert (
        "DB connection pool exhaustion caused by a reduction" not in report["candidate_root_cause"]
    )
