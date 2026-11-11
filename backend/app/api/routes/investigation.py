from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.workflow import InvestigationWorkflow
from app.database import get_incident_history, initialize_database
from app.database.approvals import save_incident_approval
from app.synthetic_data import build_incidents

router = APIRouter(prefix="/api/v1/investigations", tags=["investigation"])


class InvestigateRequest(BaseModel):
    incident_id: str


class ApprovalRequest(BaseModel):
    incident_id: str
    decision: str


def get_investigation_workflow() -> InvestigationWorkflow:
    return InvestigationWorkflow()


@router.get("/incidents")
def list_incidents() -> list[dict[str, str]]:
    return [
        {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "service": incident.service,
            "severity": incident.severity,
        }
        for incident in build_incidents()
    ]


@router.get("/{incident_id}")
def get_incident_detail(incident_id: str) -> dict[str, object]:
    incident = next((item for item in build_incidents() if item.incident_id == incident_id), None)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    return {
        "incident_id": incident.incident_id,
        "title": incident.title,
        "description": incident.description,
        "service": incident.service,
        "severity": incident.severity,
        "timestamp": incident.timestamp,
        "symptoms": incident.symptoms,
        "deployment": incident.deployment,
    }


@router.post("/analyze")
def analyze_incident(
    payload: InvestigateRequest,
    workflow: Annotated[InvestigationWorkflow, Depends(get_investigation_workflow)],
) -> dict[str, object]:
    return workflow.analyze_incident(payload.incident_id)


@router.post("/approve")
def approve_incident(payload: ApprovalRequest) -> dict[str, object]:
    decision = payload.decision.lower()
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be either 'approve' or 'reject'")

    session = initialize_database()
    approval = save_incident_approval(
        session,
        incident_id=payload.incident_id,
        decision=decision,
    )

    return {
        "incident_id": payload.incident_id,
        "approval_status": approval.status,
        "decision": approval.decision,
        "message": (
            "Remediation is authorized to proceed."
            if approval.status == "approved"
            else "Remediation is blocked pending human review."
        ),
    }


@router.get("/history/{incident_id}")
def get_history(incident_id: str) -> list[dict[str, str]]:
    session = initialize_database()
    return get_incident_history(session, incident_id=incident_id)
