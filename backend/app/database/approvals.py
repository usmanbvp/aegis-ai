from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import ApprovalEntity, IncidentEntity


def save_incident_approval(
    session: Session,
    *,
    incident_id: str,
    decision: str,
    service: str | None = None,
    recommended_action: str | None = None,
    approval_note: str | None = None,
) -> ApprovalEntity:
    normalized_decision = decision.lower().strip()
    if normalized_decision not in {"approve", "reject"}:
        raise ValueError("decision must be either 'approve' or 'reject'")

    incident = session.query(IncidentEntity).filter_by(incident_id=incident_id).first()
    service_name = service or (incident.service if incident else "unknown")
    action_text = (
        recommended_action
        or "Review the recommended remediation before making a production change."
    )
    note_text = approval_note or "A human operator has reviewed this incident recommendation."
    now = datetime.now(timezone.utc).isoformat()

    approval = session.query(ApprovalEntity).filter_by(incident_id=incident_id).first()
    if approval is None:
        approval = ApprovalEntity(
            incident_id=incident_id,
            service=service_name,
            decision=normalized_decision,
            status="approved" if normalized_decision == "approve" else "rejected",
            recommended_action=action_text,
            approval_note=note_text,
            created_at=now,
            updated_at=now,
        )
        session.add(approval)
    else:
        approval.service = service_name
        approval.decision = normalized_decision
        approval.status = "approved" if normalized_decision == "approve" else "rejected"
        approval.recommended_action = action_text
        approval.approval_note = note_text
        approval.updated_at = now

    session.commit()
    session.refresh(approval)
    return approval


def get_incident_history(session: Session, *, incident_id: str) -> list[dict[str, str]]:
    approvals = (
        session.query(ApprovalEntity)
        .filter_by(incident_id=incident_id)
        .order_by(ApprovalEntity.created_at.asc())
        .all()
    )
    return [
        {
            "incident_id": approval.incident_id,
            "service": approval.service,
            "decision": approval.decision,
            "status": approval.status,
            "recommended_action": approval.recommended_action,
            "approval_note": approval.approval_note,
            "created_at": approval.created_at,
            "updated_at": approval.updated_at,
        }
        for approval in approvals
    ]
