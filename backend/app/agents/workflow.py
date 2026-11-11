from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.llm import LLMError, ResilientLLMClient, configured_providers
from app.rag.retrieval import RetrievalService
from app.synthetic_data import build_document_corpus, build_incidents
from app.tools.evidence import IncidentEvidenceCollector

LOGGER = logging.getLogger(__name__)


class InvestigationState(TypedDict):
    incident_id: str
    service: str
    incident: Any
    evidence_documents: list[dict[str, Any]]
    tool_findings: dict[str, Any]
    candidate_root_cause: str
    confidence: float | None
    confidence_basis: str
    summary: str
    recommended_action: str
    llm: dict[str, Any]
    graph_path: list[str]


class InvestigationWorkflow:
    def __init__(
        self,
        incidents: list[Any] | None = None,
        documents: list[Any] | None = None,
        *,
        llm_client: ResilientLLMClient | None = None,
        use_configured_llm: bool = True,
        settings: Settings | None = None,
    ) -> None:
        self.incidents = incidents if incidents is not None else build_incidents()
        self.documents = documents if documents is not None else build_document_corpus()
        self.retrieval = RetrievalService(documents=self.documents)
        self.evidence_collector = IncidentEvidenceCollector()
        self.llm_client = llm_client
        if self.llm_client is None and use_configured_llm:
            resolved_settings = settings or get_settings()
            providers = configured_providers(resolved_settings)
            if providers:
                self.llm_client = ResilientLLMClient(
                    providers,
                    timeout_seconds=resolved_settings.llm_timeout_seconds,
                    max_retries=resolved_settings.llm_max_retries,
                    retry_backoff_seconds=resolved_settings.llm_retry_backoff_seconds,
                )
        self.graph = self._build_graph()

    def _load_incident(self, incident_id: str) -> Any:
        incident = next((item for item in self.incidents if item.incident_id == incident_id), None)
        if incident is None:
            raise ValueError(f"Incident {incident_id} not found")
        return incident

    def _retrieve_documents(self, state: InvestigationState) -> InvestigationState:
        incident = state["incident"]
        query = " ".join(
            [
                incident.title,
                " ".join(incident.symptoms),
            ]
        )
        evidence = self.retrieval.search(query, service=incident.service, limit=5)
        if not evidence:
            evidence = self.retrieval.search(
                " ".join(incident.symptoms), service=incident.service, limit=5
            )
        state["evidence_documents"] = evidence
        state["graph_path"].append("retrieve_documents")
        return state

    def _collect_runtime_evidence(self, state: InvestigationState) -> InvestigationState:
        incident = state["incident"]
        state["tool_findings"] = self.evidence_collector.collect(incident)
        state["graph_path"].append("collect_runtime_evidence")
        return state

    def _build_recommendation(
        self,
        incident: Any,
        action: str | None,
        findings: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            not action
            and findings["deployment"]["risky_settings"]
            and findings["logs"]["error_count"]
        ):
            action = (
                "Review the risky deployment settings alongside the observed runtime errors. Prepare a rollback "
                "or corrective change only after verifying impact and getting human approval."
            )
        if not action:
            action = (
                "Review the retrieved documentation, deployment metadata, and runtime signals to identify a "
                "safe corrective action. Do not change production until the evidence is confirmed."
            )
        return {
            "requires_human_approval": True,
            "approval_status": "pending",
            "recommended_action": action,
            "approval_note": "A human operator must confirm this recommendation before any remediation or rollout action is taken.",
        }

    def _build_timeline(
        self, incident: Any, recommendation: dict[str, Any]
    ) -> list[dict[str, str]]:
        return [
            {
                "event": "incident_received",
                "details": f"Incident {incident.incident_id} was received for {incident.service}.",
            },
            {
                "event": "documentation_review",
                "details": "Relevant runbooks and architecture notes were retrieved and ranked.",
            },
            {
                "event": "runtime_analysis",
                "details": "Deployment metadata, logs, and service metrics were correlated with the incident.",
            },
            {"event": "recommendation_ready", "details": recommendation["recommended_action"]},
        ]

    def _synthesize_summary(self, state: InvestigationState) -> InvestigationState:
        incident = state["incident"]
        evidence = state["evidence_documents"]
        tool_findings = state["tool_findings"]
        llm_status: dict[str, Any] = {
            "mode": "deterministic_fallback",
            "provider": None,
            "model": None,
            "reason": "no_provider_configured",
        }
        recommendation = ""

        if self.llm_client:
            prompt_data = {
                "incident": {
                    "id": incident.incident_id,
                    "title": incident.title,
                    "service": incident.service,
                    "severity": incident.severity,
                    "timestamp": str(incident.timestamp),
                    "description": incident.description,
                    "symptoms": incident.symptoms,
                },
                "deployment": tool_findings["deployment"],
                "runtime_findings": tool_findings,
                "retrieved_documents": [
                    {
                        "title": document.get("title"),
                        "type": document.get("document_type"),
                        "content": str(document.get("content", ""))[:1600],
                        "retrieval_score": document.get("score"),
                    }
                    for document in evidence
                ],
            }
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an incident analyst. Use only the supplied incident, retrieved documents, "
                        "deployment metadata, and runtime findings. Do not assume a hidden ground-truth cause, "
                        "invent observations, or claim certainty beyond the evidence. Distinguish observed facts "
                        "from hypotheses. Return only a JSON object with non-empty string fields: "
                        "candidate_root_cause, summary, recommended_action. Keep the action reversible and "
                        "require human approval before production changes."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_data, ensure_ascii=True, default=str),
                },
            ]
            try:
                completion = self.llm_client.complete(messages)
                candidate = self._validated_text(completion.content, "candidate_root_cause", 500)
                summary = self._validated_text(completion.content, "summary", 1800)
                recommendation = self._validated_text(completion.content, "recommended_action", 900)
                llm_status = {
                    "mode": "llm",
                    "provider": completion.provider,
                    "model": completion.model,
                    "reason": None,
                }
                confidence = None
                confidence_basis = "not_calibrated"
            except (LLMError, ValueError) as error:
                reason = error.code if isinstance(error, LLMError) else "invalid_assessment"
                LOGGER.warning("LLM synthesis failed (%s); using evidence-only fallback.", reason)
                llm_status["reason"] = reason
                candidate, summary, confidence = self._fallback_synthesis(
                    incident, evidence, tool_findings
                )
                confidence_basis = "heuristic_evidence_coverage_not_calibrated_probability"
        else:
            candidate, summary, confidence = self._fallback_synthesis(
                incident, evidence, tool_findings
            )
            confidence_basis = "heuristic_evidence_coverage_not_calibrated_probability"

        state["candidate_root_cause"] = candidate
        state["confidence"] = round(confidence, 3) if confidence is not None else None
        state["confidence_basis"] = confidence_basis
        state["summary"] = summary
        state["recommended_action"] = recommendation
        state["llm"] = llm_status
        state["graph_path"].append("synthesize_summary")
        return state

    @staticmethod
    def _validated_text(content: dict[str, Any], key: str, max_length: int) -> str:
        value = content.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"LLM assessment field {key!r} is missing or empty.")
        return value.strip()[:max_length]

    @staticmethod
    def _fallback_synthesis(
        incident: Any,
        evidence: list[dict[str, Any]],
        findings: dict[str, Any],
    ) -> tuple[str, str, float]:
        latest_error = findings["logs"].get("latest_error")
        risky_settings = findings["deployment"].get("risky_settings", [])
        if latest_error:
            candidate = f"Potential cause indicated by the latest runtime error: {latest_error}."
        elif risky_settings:
            candidate = (
                "A deployment configuration change may be contributing to the incident; "
                "verify it against runtime evidence."
            )
        else:
            candidate = "Available evidence does not establish a single root cause; further investigation is required."

        metric_peak = findings["metrics"].get("db_connection_usage_peak")
        evidence_facts = [
            f"{findings['logs']['error_count']} runtime errors were observed",
            f"{len(evidence)} related documents were retrieved",
        ]
        if metric_peak is not None:
            evidence_facts.append(f"peak database connection usage was {metric_peak}%")
        if risky_settings:
            evidence_facts.append(
                f"deployment risk signals were observed: {', '.join(risky_settings)}"
            )
        summary = (
            f"Evidence-only fallback for {incident.service}: {candidate} "
            + "; ".join(evidence_facts)
            + ". These signals are observations, not a calibrated probability or confirmed root cause."
        )
        coverage_signals = [
            bool(evidence),
            bool(findings["logs"]["error_count"]),
            metric_peak is not None,
            bool(risky_settings),
        ]
        heuristic_score = sum(coverage_signals) / len(coverage_signals)
        return candidate, summary, heuristic_score

    def _build_graph(self) -> Any:
        graph = StateGraph(InvestigationState)
        graph.add_node("retrieve_documents", self._retrieve_documents)
        graph.add_node("collect_runtime_evidence", self._collect_runtime_evidence)
        graph.add_node("synthesize_summary", self._synthesize_summary)
        graph.add_edge(START, "retrieve_documents")
        graph.add_edge("retrieve_documents", "collect_runtime_evidence")
        graph.add_edge("collect_runtime_evidence", "synthesize_summary")
        graph.add_edge("synthesize_summary", END)
        return graph.compile()

    def analyze_incident(self, incident_id: str) -> dict[str, Any]:
        incident = self._load_incident(incident_id)
        initial_state: InvestigationState = {
            "incident_id": incident.incident_id,
            "service": incident.service,
            "incident": incident,
            "evidence_documents": [],
            "tool_findings": {},
            "candidate_root_cause": "",
            "confidence": 0.0,
            "confidence_basis": "",
            "summary": "",
            "recommended_action": "",
            "llm": {},
            "graph_path": [],
        }
        final_state = self.graph.invoke(initial_state)
        recommendation = self._build_recommendation(
            incident,
            final_state["recommended_action"] or None,
            final_state["tool_findings"],
        )
        timeline = self._build_timeline(incident, recommendation)
        return {
            "incident_id": final_state["incident_id"],
            "service": final_state["service"],
            "severity": incident.severity,
            "title": incident.title,
            "candidate_root_cause": final_state["candidate_root_cause"],
            "confidence": final_state["confidence"],
            "confidence_basis": final_state["confidence_basis"],
            "evidence_documents": final_state["evidence_documents"],
            "tool_findings": final_state["tool_findings"],
            "summary": final_state["summary"],
            "recommendation": recommendation,
            "timeline": timeline,
            "graph_path": final_state["graph_path"],
            "llm": final_state["llm"],
        }
