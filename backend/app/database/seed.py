from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import (
    DeploymentEntity,
    DocumentEntity,
    IncidentEntity,
    LogEntryEntity,
    MetricSampleEntity,
    ServiceEntity,
)
from app.synthetic_data import build_deployments, build_document_corpus, build_incidents, build_logs, build_metrics, build_service_catalog


def seed_database(session: Session | None = None, *, dataset_dir: str | None = None) -> dict[str, int]:
    if session is None:
        from app.database.connection import initialize_database

        session = initialize_database()

    incidents = build_incidents()
    documents = build_document_corpus()
    services = build_service_catalog()
    deployments = build_deployments()
    logs = build_logs()
    metrics = build_metrics()

    for service in services:
        session.add(
            ServiceEntity(
                name=service.name,
                version=service.version,
                environment=service.environment,
                owner=service.owner,
                status=service.status,
                dependencies=service.dependencies,
            )
        )

    for deployment in deployments:
        session.add(
            DeploymentEntity(
                deployment_id=deployment.deployment_id,
                service=deployment.service,
                version=deployment.version,
                timestamp=deployment.timestamp,
                environment=deployment.environment,
                configuration_changes=deployment.configuration_changes,
            )
        )

    for incident in incidents:
        session.add(
            IncidentEntity(
                incident_id=incident.incident_id,
                title=incident.title,
                description=incident.description,
                service=incident.service,
                timestamp=incident.timestamp,
                severity=incident.severity,
                symptoms=incident.symptoms,
                ground_truth_root_cause=incident.ground_truth_root_cause,
                relevant_document_ids=incident.relevant_document_ids,
                expected_log_patterns=incident.expected_log_patterns,
                expected_metric_patterns=incident.expected_metric_patterns,
                deployment=incident.deployment,
                expected_evidence=incident.expected_evidence,
            )
        )

    for document in documents:
        session.add(
            DocumentEntity(
                document_id=document.document_id,
                title=document.title,
                service=document.service,
                document_type=document.document_type,
                tags=document.tags,
                created_at=document.created_at,
                content=document.content,
            )
        )

    for log in logs:
        session.add(
            LogEntryEntity(
                timestamp=log.timestamp,
                service=log.service,
                level=log.level,
                endpoint=log.endpoint,
                status_code=log.status_code,
                latency_ms=log.latency_ms,
                error_type=log.error_type,
                message=log.message,
                trace_id=log.trace_id,
                deployment_id=log.deployment_id,
            )
        )

    for metric in metrics:
        session.add(
            MetricSampleEntity(
                timestamp=metric.timestamp,
                service=metric.service,
                metric=metric.metric,
                value=metric.value,
                unit=metric.unit,
                deployment_id=metric.deployment_id,
            )
        )

    session.commit()

    stats = {
        "incidents": len(incidents),
        "documents": len(documents),
        "services": len(services),
        "deployments": len(deployments),
        "logs": len(logs),
        "metrics": len(metrics),
    }
    return stats
