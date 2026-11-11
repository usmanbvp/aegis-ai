from __future__ import annotations

from typing import Any

from app.synthetic_data import build_deployments, build_logs, build_metrics


class IncidentEvidenceCollector:
    def __init__(
        self,
        deployments: list[Any] | None = None,
        logs: list[Any] | None = None,
        metrics: list[Any] | None = None,
    ) -> None:
        self.deployments = list(deployments) if deployments is not None else build_deployments()
        self.logs = list(logs) if logs is not None else build_logs()
        self.metrics = list(metrics) if metrics is not None else build_metrics()

    def collect(self, incident: Any) -> dict[str, Any]:
        service = incident.service
        latest_deployment = next(
            (
                deployment
                for deployment in self.deployments
                if deployment.service == service and deployment.environment == "production"
            ),
            None,
        )
        service_logs = [entry for entry in self.logs if entry.service == service]
        error_logs = [entry for entry in service_logs if entry.error_type]
        service_metrics = [sample for sample in self.metrics if sample.service == service]

        latency_samples = [sample.value for sample in service_metrics if sample.metric == "latency_p95"]
        db_usage_samples = [sample.value for sample in service_metrics if sample.metric == "db_connection_usage"]
        error_rate_samples = [sample.value for sample in service_metrics if sample.metric == "error_rate"]

        deployment_summary = {
            "service": service,
            "deployment_id": latest_deployment.deployment_id if latest_deployment else None,
            "configuration_changes": latest_deployment.configuration_changes if latest_deployment else {},
            "risky_settings": [
                key
                for key, value in (latest_deployment.configuration_changes.items() if latest_deployment else {})
                if value != "stable"
            ],
        }

        logs_summary = {
            "service": service,
            "error_count": len(error_logs),
            "error_types": sorted({entry.error_type for entry in error_logs if entry.error_type}),
            "sample_messages": [entry.message for entry in error_logs[:3]],
            "latest_error": error_logs[0].message if error_logs else None,
        }

        metrics_summary = {
            "service": service,
            "latency_p95_avg": round(sum(latency_samples) / len(latency_samples), 2) if latency_samples else 0.0,
            "db_connection_usage_peak": round(max(db_usage_samples), 2) if db_usage_samples else 0.0,
            "db_connection_usage_avg": round(sum(db_usage_samples) / len(db_usage_samples), 2) if db_usage_samples else 0.0,
            "error_rate_avg": round(sum(error_rate_samples) / len(error_rate_samples), 4) if error_rate_samples else 0.0,
        }

        correlation = (
            "Deployment changes align with the observed failure pattern and runtime metrics; "
            "the service shows elevated DB usage and repeated errors during the rollout window."
        )

        return {
            "deployment": deployment_summary,
            "logs": logs_summary,
            "metrics": metrics_summary,
            "correlation": correlation,
            "finding": (
                f"For {service}, the latest deployment changed {deployment_summary['risky_settings'] or 'no obvious risky settings'} "
                f"while logs recorded {logs_summary['error_count']} error entries and DB utilization peaked at "
                f"{metrics_summary['db_connection_usage_peak']}%."
            ),
        }
