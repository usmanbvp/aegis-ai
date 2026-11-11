from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    description: str
    service: str
    timestamp: str
    severity: str
    symptoms: list[str]
    ground_truth_root_cause: str
    relevant_document_ids: list[str]
    expected_log_patterns: list[str]
    expected_metric_patterns: list[str]
    deployment: dict[str, Any]
    expected_evidence: list[str]

    model_config = ConfigDict(extra="forbid")


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    service: str
    document_type: str
    tags: list[str]
    created_at: str
    content: str

    model_config = ConfigDict(extra="forbid")


class ServiceRecord(BaseModel):
    name: str
    version: str
    environment: str
    owner: str
    status: str
    dependencies: list[str]

    model_config = ConfigDict(extra="forbid")


class DeploymentRecord(BaseModel):
    deployment_id: str
    service: str
    version: str
    timestamp: str
    environment: str
    configuration_changes: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class LogEntry(BaseModel):
    timestamp: str
    service: str
    level: str
    endpoint: str
    status_code: int
    latency_ms: int
    error_type: str | None = None
    message: str
    trace_id: str
    deployment_id: str

    model_config = ConfigDict(extra="forbid")


class MetricSample(BaseModel):
    timestamp: str
    service: str
    metric: str
    value: float
    unit: str
    deployment_id: str

    model_config = ConfigDict(extra="forbid")


SERVICE_CATALOG: dict[str, dict[str, Any]] = {
    "checkout-api": {
        "version": "v2.8.6",
        "owner": "commerce-platform",
        "status": "degraded",
        "dependencies": ["postgres", "redis", "inventory-api"],
    },
    "payments-api": {
        "version": "v3.1.2",
        "owner": "finance-platform",
        "status": "healthy",
        "dependencies": ["postgres", "billing-worker", "auth-service"],
    },
    "inventory-api": {
        "version": "v1.9.7",
        "owner": "catalog-platform",
        "status": "healthy",
        "dependencies": ["postgres", "redis", "search-api"],
    },
    "search-api": {
        "version": "v2.3.0",
        "owner": "catalog-platform",
        "status": "healthy",
        "dependencies": ["redis", "catalog-api", "postgres"],
    },
    "auth-service": {
        "version": "v5.2.9",
        "owner": "identity-platform",
        "status": "degraded",
        "dependencies": ["postgres", "redis", "oauth-provider"],
    },
    "notification-worker": {
        "version": "v1.4.8",
        "owner": "messaging-platform",
        "status": "healthy",
        "dependencies": ["redis", "postgres", "email-gateway"],
    },
    "user-profile-api": {
        "version": "v4.2.1",
        "owner": "identity-platform",
        "status": "healthy",
        "dependencies": ["postgres", "redis", "auth-service"],
    },
    "recommendations-api": {
        "version": "v2.7.1",
        "owner": "growth-platform",
        "status": "healthy",
        "dependencies": ["redis", "catalog-api", "search-api"],
    },
    "billing-worker": {
        "version": "v2.0.4",
        "owner": "finance-platform",
        "status": "healthy",
        "dependencies": ["postgres", "payments-api"],
    },
    "catalog-api": {
        "version": "v3.5.0",
        "owner": "catalog-platform",
        "status": "healthy",
        "dependencies": ["postgres", "redis", "search-api"],
    },
    "gateway-api": {
        "version": "v6.1.9",
        "owner": "platform-ops",
        "status": "healthy",
        "dependencies": ["auth-service", "checkout-api", "inventory-api"],
    },
    "order-events-worker": {
        "version": "v1.8.4",
        "owner": "commerce-platform",
        "status": "healthy",
        "dependencies": ["postgres", "kafka", "checkout-api"],
    },
}

SERVICE_DOC_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "checkout-api": [
        {
            "title": "Checkout API DB Pool Tuning Guide",
            "document_type": "runbook",
            "content": "Checkout API depends on Postgres for order creation and payment validation. A sustained DB connection saturation above 85% on the checkout pool causes request queueing and p95 latency spikes. When connection usage remains above 90% for 5 minutes, inspect pool settings, query locks, and recent deploy changes. Recovery is to revert a recent pool config change or scale the database connection pool in the service configuration.",
        },
        {
            "title": "Checkout Dependency Architecture",
            "document_type": "architecture",
            "content": "The checkout API calls inventory-api, payments-api, and Postgres in a single request path. DB connections are pooled per pod and each web request opens a short-lived transaction during order processing. If the deployment config reduces max_connections or increases the number of replicas without adjusting pool capacity, the checkout API will exhibit timeout cascades and elevated latency.",
        },
        {
            "title": "Checkout Deployment Checklist",
            "document_type": "deployment",
            "content": "Before deploying the checkout API, validate environment overrides that alter database pool configuration, thread counts, and connection timeout values. Common misconfigurations include setting DB max pool size too low and raising the connection idle time too aggressively. Confirm the deployment metadata includes the exact config changes and verify HTTP 5xx and DB timeout ratios after the rollout.",
        },
    ],
    "payments-api": [
        {
            "title": "Payments API Retry and Timeout Policy",
            "document_type": "runbook",
            "content": "Payments API must not retry idempotent payment calls beyond the configured budget. Failures in the upstream billing-worker or timeouts to Postgres should trigger backoff and circuit breaking. Repeated timeouts coupled with queue depth increases often point to database lock contention or a configuration regression rather than a network issue.",
        },
        {
            "title": "Payments Dependency Map",
            "document_type": "architecture",
            "content": "The payments API writes to Postgres and uses billing-worker for asynchronous settlement. If worker backlog is elevated or the billing pipeline is under-provisioned, API latency can increase even when the primary API remains up. Check the dependency health before blaming the application layer.",
        },
        {
            "title": "Payment Deployment Safety Notes",
            "document_type": "deployment",
            "content": "Any change to queue concurrency, HTTP client timeout, or database pool sizing should be deployed with validation steps. A deployment that sets a low max pool value or a high default timeout can generate 'timeout waiting for connection' errors after a rollout to production.",
        },
    ],
    "inventory-api": [
        {
            "title": "Inventory Cache Miss Handling",
            "document_type": "runbook",
            "content": "Inventory API performance depends on Redis cache hit rate. When the cache miss rate jumps above 35%, the service begins to surge on Postgres reads and may increase p99 latency. Always inspect the cache hit rate for the deployment that introduced the new catalog indexing or invalidation logic.",
        },
        {
            "title": "Inventory Architecture Notes",
            "document_type": "architecture",
            "content": "Inventory service reads from Redis and Postgres as part of checkout order validation. Misconfigured invalidation keys or a stale cache can cause a storm of cache misses, leading to a sustained read amplification that appears as elevated DB load.",
        },
        {
            "title": "Inventory Deployment Validation",
            "document_type": "deployment",
            "content": "Validate Redis dependency health and cache TTL values before rolling out inventory changes. A deployment that changes cache key names without a warmup or invalidation strategy will generate a miss storm and heavy Postgres pressure.",
        },
    ],
    "search-api": [
        {
            "title": "Search API Index Sync Runbook",
            "document_type": "runbook",
            "content": "The search API depends on Redis and the catalog service for fast product lookups. If a deployment updates index names or invalidates stale cache keys, service response times increase sharply and downstream catalog requests queue. Check for index drift and stale cache keys before escalating to infrastructure incidents.",
        },
        {
            "title": "Search Architecture Overview",
            "document_type": "architecture",
            "content": "Search API receives product requests through the gateway and reads from Redis-backed metadata with occasional catalog fallback. A severe cache invalidation change with a low TTL can create request amplification and downstream database load.",
        },
        {
            "title": "Search Deployment Checks",
            "document_type": "deployment",
            "content": "Review deployment diffs for cache invalidation configuration, request timeout tuning, and upstream catalog connection pool changes. Search services should keep TTL values stable across deployments to avoid bursty cache misses and a sustained latency increase.",
        },
    ],
    "auth-service": [
        {
            "title": "Auth JWT Validation Troubleshooting",
            "document_type": "runbook",
            "content": "The auth-service validates JWTs and token refreshes against Redis and Postgres. If a deployment creates a mismatch in issuer or token secret configuration, users experience 401 errors and elevated login retries. Confirm the app environment and secret rotation state in the deployment metadata.",
        },
        {
            "title": "Auth Service Dependency Diagram",
            "document_type": "architecture",
            "content": "Auth-service is on the critical path for all transaction traffic. A dependency or configuration issue in Redis for token store or the token issuer config can create user-visible authentication failures that cascade to the gateway and other dependent services.",
        },
        {
            "title": "Auth Deployment Guardrails",
            "document_type": "deployment",
            "content": "Any deployment altering JWT issuer, secret rotation, or Redis cache names must include validation of login success rate and 401 patterns. A single bad environment variable can fail authentication globally without triggering application-level exceptions.",
        },
    ],
    "notification-worker": [
        {
            "title": "Notification Worker Backlog Guidance",
            "document_type": "runbook",
            "content": "The notification worker processes email and SMS messages from a queue and writes to Redis before sending. If queue depth exceeds 5,000 messages for more than five minutes, investigate worker concurrency settings and upstream dependency health. Queue backlog is usually caused by a downstream email provider latency or worker crash, not the queue itself.",
        },
        {
            "title": "Notification Worker Architecture",
            "document_type": "architecture",
            "content": "This worker consumes from a queue, writes status to Postgres, and triggers the email gateway. A backlog often arises when consumer concurrency is reduced or the email gateway is slow. The symptom differs from a compute saturation issue because CPU remains low while queue depth climbs.",
        },
        {
            "title": "Notification Deployment Review",
            "document_type": "deployment",
            "content": "Any deployment that changes queue concurrency or retry delay should be validated against backlog depth and delivery success rate. A worker deployment with too many retries or a mismatched queue name can silently degrade delivery without immediate API-level errors.",
        },
    ],
    "user-profile-api": [
        {
            "title": "Profile API Saturation Guide",
            "document_type": "runbook",
            "content": "The user profile API sees steady traffic and reads from Redis before falling back to Postgres. If Redis connectivity is flaky, the service begins to experience latency and elevated DB read contention. Force-check Redis health and confirm the service is not using a stale secret or IAM credential.",
        },
        {
            "title": "Profile API Architecture",
            "document_type": "architecture",
            "content": "User profile requests depend on the auth-service and Redis for session and caching operations. If auth-service dependencies fail or Redis becomes unavailable, the profile service produces both latency and inconsistent 5xx response patterns that appear as a service outage.",
        },
        {
            "title": "Profile Deployment Notes",
            "document_type": "deployment",
            "content": "Deployment validation must include Redis connection parameters and auth-service dependency health. A configuration mismatch in the token store or application environment can trigger 5xx errors while keeping overall infrastructure nominal.",
        },
    ],
    "recommendations-api": [
        {
            "title": "Recommendation Warm Cache Playbook",
            "document_type": "runbook",
            "content": "Recommendations API relies on search and catalog data. Cache invalidation errors or stale recommendation state can produce a high miss rate and increase Redis pressure. Monitor Redis cache hit rate, response latency, and request volume during a deployment to isolate cache issues from upstream traffic spikes.",
        },
        {
            "title": "Recommendation Service Overview",
            "document_type": "architecture",
            "content": "The recommendations API depends on Redis to serve personalized suggestions while reading product metadata from catalog and search. A cache cold-start or invalidation bug can create broad request fan-out and saturation of downstream dependencies.",
        },
        {
            "title": "Recommendation Deployment Checklist",
            "document_type": "deployment",
            "content": "Validate cache TTL and invalidation keys before rollouts. If recommendation metadata changes without a corresponding warmup strategy, the service rapidly becomes a traffic multiplier for downstream catalog and search APIs.",
        },
    ],
    "billing-worker": [
        {
            "title": "Billing Worker Queue Health",
            "document_type": "runbook",
            "content": "The billing worker handles settlement jobs from the queue. If worker concurrency is reduced or jobs are not retried correctly, queue depth rises. Unlike service API latency, billing-worker issues manifest as delayed job processing and order settlement errors.",
        },
        {
            "title": "Billing Worker Architecture",
            "document_type": "architecture",
            "content": "The billing worker consumes payment events and writes settlement records to Postgres. A queue misconfiguration, a database lock, or a dependency issue can cause backlog growth without direct API errors. Inspect the queue and database connection pool before rolling back the deployment.",
        },
        {
            "title": "Billing Deployment Audits",
            "document_type": "deployment",
            "content": "Review queue retry policy and worker concurrency on every deployment. Inconsistent worker settings can create long job backlogs even though the main API remains one step removed from the actual outage.",
        },
    ],
    "catalog-api": [
        {
            "title": "Catalog API Slow Query Review",
            "document_type": "runbook",
            "content": "Catalog API response latency is often caused by a database query regression or an overly broad Redis query path. If a deployment changes a query to use a non-indexed filter, p95 latency spikes without direct dependency failures. Always compare pre- and post-deployment query plans.",
        },
        {
            "title": "Catalog Dependency Layout",
            "document_type": "architecture",
            "content": "Catalog API reads from Postgres and caches product metadata in Redis. A query regression or repeated cache misses can amplify traffic and create visible user-facing latency even when the service still returns HTTP 200s.",
        },
        {
            "title": "Catalog Deployment Safety",
            "document_type": "deployment",
            "content": "Check query-plans and index creation changes in deployment metadata before rollout. Large data model changes can slow the catalog service without an obvious infrastructure failure pattern.",
        },
    ],
    "gateway-api": [
        {
            "title": "Gateway Traffic Routing Guide",
            "document_type": "runbook",
            "content": "The gateway API sits in front of all customer traffic and routes to dependent services. A bad upstream service configuration or dependency timeout cascade can create 5xx spikes at the API edge. Review the routing config and retry budget before attributing the issue to the gateway itself.",
        },
        {
            "title": "Gateway Architecture Notes",
            "document_type": "architecture",
            "content": "The gateway aggregates requests to checkout, auth, recommendations, and catalog services. When downstream services fail and the gateway keeps retrying, the user latency rises before a root dependency is repaired. The gateway should keep a tight retry budget to prevent a timeout cascade.",
        },
        {
            "title": "Gateway Deployment Checklist",
            "document_type": "deployment",
            "content": "All gateway changes should include retry budget, timeout values, and downstream circuit-breaker settings. A deployment that adds retries without a circuit breaker can magnify dependency issues into an outage at the edge.",
        },
    ],
    "order-events-worker": [
        {
            "title": "Order Events Queue Recovery",
            "document_type": "runbook",
            "content": "The order events worker consumes purchase events and records updates in Postgres. If the backlog grows while the worker is healthy, inspect queue lag, consumer concurrency, and database insert latency. This failure class produces an order-visibility delay rather than user-facing login or checkout errors.",
        },
        {
            "title": "Order Events Dependency Layout",
            "document_type": "architecture",
            "content": "Order events processing writes to Postgres and depends on the checkout API and Kafka. A backlog usually indicates a consumer mismatch or a database write regression rather than a source issue in the upstream API itself.",
        },
        {
            "title": "Order Events Deployment Checks",
            "document_type": "deployment",
            "content": "Review queue config, concurrency, and database write timeout modifications. A deployment that increases worker parallelism without adjusting database writes can create queue lag even while the API continues to answer some requests.",
        },
    ],
}


def iso_now(offset_minutes: int = 0) -> str:
    current = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return current.isoformat().replace("+00:00", "Z")


def incident_templates() -> list[dict[str, Any]]:
    return [
        {
            "service": "checkout-api",
            "root_cause": "DB connection pool exhaustion caused by a reduction in max_connections during deployment",
            "symptoms": ["p95 latency increased after deployment", "DB timeout errors appeared in checkout", "5xx error rate surged"],
            "severity": "SEV-1",
            "deployment_change": "max_connections lowered from 200 to 80 and idle_timeout increased",
            "expected_log": ["DB_CONNECTION_TIMEOUT", "connection pool exhausted"],
            "expected_metric": ["db_connection_usage", "error_rate", "latency_p95"],
        },
        {
            "service": "checkout-api",
            "root_cause": "Redis timeout cascade caused by stale connection pool settings after rollout",
            "symptoms": ["checkout requests timing out", "inventory calls slowed", "error budget exceeded"],
            "severity": "SEV-1",
            "deployment_change": "Redis client retries disabled and socket timeout increased",
            "expected_log": ["REDIS_TIMEOUT", "socket timeout"],
            "expected_metric": ["latency_p99", "redis_timeout_count", "error_rate"],
        },
        {
            "service": "inventory-api",
            "root_cause": "Redis cache invalidation bug created a cache miss storm",
            "symptoms": ["cache hit rate collapsed", "inventory queries slowed", "read load on Postgres increased"],
            "severity": "SEV-2",
            "deployment_change": "cache key prefix changed without warmup",
            "expected_log": ["CACHE_MISS_STORM", "redis lookup failures"],
            "expected_metric": ["cache_hit_rate", "db_connection_usage", "latency_p95"],
        },
        {
            "service": "search-api",
            "root_cause": "Search API index name mismatch after release caused stale requests and fallback latency",
            "symptoms": ["search latency spiked", "catalog requests queued", "user-facing search degraded"],
            "severity": "SEV-2",
            "deployment_change": "index version mismatch and stale cache keys",
            "expected_log": ["INDEX_NOT_FOUND", "cache invalidation"],
            "expected_metric": ["cache_hit_rate", "latency_p95", "request_count"],
        },
        {
            "service": "auth-service",
            "root_cause": "JWT issuer configuration drift caused 401 failures across all login traffic",
            "symptoms": ["logins failing", "gateway 401 spike", "user sessions dropped"],
            "severity": "SEV-1",
            "deployment_change": "issuer secret rotation without env sync",
            "expected_log": ["JWT_VERIFICATION_FAILED", "invalid issuer"],
            "expected_metric": ["error_rate", "auth_failure_rate", "request_count"],
        },
        {
            "service": "notification-worker",
            "root_cause": "Worker concurrency reduced while retry policy increased queue backlog",
            "symptoms": ["email backlog grew", "worker utilization dropped", "delivery latency increased"],
            "severity": "SEV-3",
            "deployment_change": "retry delay doubled and concurrency capped",
            "expected_log": ["QUEUE_BACKLOG", "delayed processing"],
            "expected_metric": ["queue_depth", "worker_throughput", "delivery_latency"],
        },
        {
            "service": "payments-api",
            "root_cause": "Billing worker timeout caused downstream payment retries and API latency regression",
            "symptoms": ["payment calls slow", "timeouts on settlement", "retry loops increased"],
            "severity": "SEV-1",
            "deployment_change": "request timeout increased without backpressure",
            "expected_log": ["BILLING_TIMEOUT", "HTTP 504"],
            "expected_metric": ["latency_p99", "error_rate", "queue_depth"],
        },
        {
            "service": "catalog-api",
            "root_cause": "Database query regression from new unindexed filter created latency amplification",
            "symptoms": ["catalog endpoints degraded", "p95 latency screamed", "db CPU increased"],
            "severity": "SEV-2",
            "deployment_change": "new filter added without index and sort tuning",
            "expected_log": ["QUERY_TIMEOUT", "slow query"],
            "expected_metric": ["latency_p95", "db_cpu_usage", "query_duration"],
        },
        {
            "service": "gateway-api",
            "root_cause": "Retry storm from downstream dependency failures amplified 5xx errors at edge",
            "symptoms": ["gateway 5xx spike", "upstream retry rate high", "all services impacted"],
            "severity": "SEV-1",
            "deployment_change": "retry budget raised without circuit breaker",
            "expected_log": ["RETRY_STORM", "upstream timeout"],
            "expected_metric": ["error_rate", "latency_p95", "upstream_retry_count"],
        },
        {
            "service": "order-events-worker",
            "root_cause": "No-op database write throttling created event backlog after deployment",
            "symptoms": ["order events lagged", "event queue depth grew", "order sync delays increased"],
            "severity": "SEV-3",
            "deployment_change": "consumers reduced and DB batch size lowered",
            "expected_log": ["EVENT_QUEUE_LAG", "write timeout"],
            "expected_metric": ["queue_depth", "db_write_latency", "event_lag"],
        },
    ]


def build_incidents() -> list[IncidentRecord]:
    incidents: list[IncidentRecord] = []
    base_templates = incident_templates()
    for index, template in enumerate(base_templates * 5):
        service = template["service"]
        window_offset = index * 18
        incident_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=window_offset)
        deployment_id = f"dep-{service.replace('-', '')}-{index + 1:03d}"
        doc_ids = [
            f"doc-{service}-{doc_index:02d}"
            for doc_index in range(1, 4)
        ]
        incidents.append(
            IncidentRecord(
                incident_id=f"INC-{index + 1:03d}",
                title=f"{service.title()} incident after {template['severity']} deployment",
                description=(
                    f"The {service} began to show {', '.join(template['symptoms'][:2])} immediately after the latest deploy. "
                    f"Investigate the incident and identify the likely root cause."
                ),
                service=service,
                timestamp=incident_time.isoformat().replace("+00:00", "Z"),
                severity=template["severity"],
                symptoms=template["symptoms"],
                ground_truth_root_cause=template["root_cause"],
                relevant_document_ids=doc_ids,
                expected_log_patterns=template["expected_log"],
                expected_metric_patterns=template["expected_metric"],
                deployment={
                    "deployment_id": deployment_id,
                    "service": service,
                    "version": SERVICE_CATALOG[service]["version"],
                    "environment": "production",
                    "configuration_changes": {
                        "summary": template["deployment_change"],
                        "risky_settings": ["timeout", "pool_size", "cache_ttl"],
                    },
                },
                expected_evidence=[
                    f"Deployment metadata for {service} shows {template['deployment_change']}",
                    f"Logs are dominated by {template['expected_log'][0]}",
                    f"Metrics show a sustained abnormal increase in {template['expected_metric'][0]}",
                    f"Service runbook for {service} recommends checking the same dependency path",
                ],
            )
        )
    return incidents


def build_document_corpus() -> list[DocumentRecord]:
    docs: list[DocumentRecord] = []
    doc_index = 1
    for service, templates in SERVICE_DOC_TEMPLATES.items():
        for template in templates:
            doc_id = f"doc-{service}-{doc_index:02d}"
            docs.append(
                DocumentRecord(
                    document_id=doc_id,
                    title=template["title"],
                    service=service,
                    document_type=template["document_type"],
                    tags=[service.replace('-', '_'), template["document_type"], "incident-review"],
                    created_at=iso_now(-1800 + doc_index * 5),
                    content=template["content"],
                )
            )
            doc_index += 1
    return docs


def build_service_catalog() -> list[ServiceRecord]:
    records: list[ServiceRecord] = []
    for service, metadata in SERVICE_CATALOG.items():
        records.append(
            ServiceRecord(
                name=service,
                version=metadata["version"],
                environment="production",
                owner=metadata["owner"],
                status=metadata["status"],
                dependencies=metadata["dependencies"],
            )
        )
    return records


def build_deployments() -> list[DeploymentRecord]:
    records: list[DeploymentRecord] = []
    for service, metadata in SERVICE_CATALOG.items():
        for deployment_index in range(1, 4):
            records.append(
                DeploymentRecord(
                    deployment_id=f"dep-{service.replace('-', '')}-{deployment_index:02d}",
                    service=service,
                    version=metadata["version"],
                    timestamp=iso_now(-(deployment_index * 180) + 60),
                    environment="production",
                    configuration_changes={
                        "db_pool": "lowered" if service in {"checkout-api", "payments-api"} else "stable",
                        "cache_ttl": "reduced" if service in {"inventory-api", "search-api"} else "stable",
                        "timeout": "increased" if service in {"gateway-api", "auth-service"} else "stable",
                    },
                )
            )
    return records


def build_logs() -> list[LogEntry]:
    logs: list[LogEntry] = []
    for service in SERVICE_CATALOG:
        for minute in range(0, 48):
            time_stamp = datetime(2026, 8, 1, 9, 20, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
            error_type = "DB_CONNECTION_TIMEOUT" if service == "checkout-api" and minute % 6 == 0 else "HTTP_504" if service in {"gateway-api", "payments-api"} and minute % 7 == 0 else "CACHE_MISS" if service in {"inventory-api", "search-api"} and minute % 5 == 0 else "JWT_VERIFICATION_FAILED" if service == "auth-service" and minute % 8 == 0 else "QUEUE_BACKLOG" if service == "notification-worker" and minute % 4 == 0 else None
            logs.append(
                LogEntry(
                    timestamp=time_stamp.isoformat().replace("+00:00", "Z"),
                    service=service,
                    level="ERROR" if error_type else "INFO",
                    endpoint=f"/{service}/v1/checkout" if service == "checkout-api" else f"/{service}/health",
                    status_code=503 if error_type else 200,
                    latency_ms=450 + (minute % 10) * 60 if error_type else 120 + (minute % 5) * 12,
                    error_type=error_type,
                    message=(
                        "DB connection pool exhausted" if error_type == "DB_CONNECTION_TIMEOUT"
                        else "Upstream dependency timed out" if error_type == "HTTP_504"
                        else "Cache invalidation storm detected" if error_type == "CACHE_MISS"
                        else "JWT verification failed due to issuer mismatch" if error_type == "JWT_VERIFICATION_FAILED"
                        else "Queue lag exceeded threshold" if error_type == "QUEUE_BACKLOG"
                        else "Service request completed successfully"
                    ),
                    trace_id=f"trace-{service}-{minute:03d}",
                    deployment_id=f"dep-{service.replace('-', '')}-01",
                )
            )
    return logs


def build_metrics() -> list[MetricSample]:
    metric_samples: list[MetricSample] = []
    for service in SERVICE_CATALOG:
        for minute in range(0, 48):
            time_stamp = datetime(2026, 8, 1, 9, 20, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
            base = 60 if service in {"checkout-api", "payments-api"} else 40
            metric_samples.append(
                MetricSample(
                    timestamp=time_stamp.isoformat().replace("+00:00", "Z"),
                    service=service,
                    metric="latency_p95",
                    value=float(base + ((minute * 7) % 45)),
                    unit="ms",
                    deployment_id=f"dep-{service.replace('-', '')}-01",
                )
            )
            metric_samples.append(
                MetricSample(
                    timestamp=time_stamp.isoformat().replace("+00:00", "Z"),
                    service=service,
                    metric="error_rate",
                    value=float(0.03 + ((minute * 11) % 9) / 100),
                    unit="ratio",
                    deployment_id=f"dep-{service.replace('-', '')}-01",
                )
            )
            metric_samples.append(
                MetricSample(
                    timestamp=time_stamp.isoformat().replace("+00:00", "Z"),
                    service=service,
                    metric="db_connection_usage",
                    value=float(40 + ((minute * 17) % 60)),
                    unit="percent",
                    deployment_id=f"dep-{service.replace('-', '')}-01",
                )
            )
    return metric_samples


def write_dataset(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    incidents_path = output_dir / "incidents" / "incident_scenarios.json"
    docs_path = output_dir / "documents" / "document_corpus.json"
    services_path = output_dir / "services" / "service_catalog.json"
    deployments_path = output_dir / "deployments" / "deployments.json"
    logs_path = output_dir / "logs" / "system_logs.json"
    metrics_path = output_dir / "metrics" / "service_metrics.json"

    for path in [incidents_path, docs_path, services_path, deployments_path, logs_path, metrics_path]:
        path.parent.mkdir(parents=True, exist_ok=True)

    incidents = build_incidents()
    documents = build_document_corpus()
    services = build_service_catalog()
    deployments = build_deployments()
    logs = build_logs()
    metrics = build_metrics()

    incidents_path.write_text("\n".join([r.model_dump_json() for r in incidents]), encoding="utf-8")
    docs_path.write_text("\n".join([r.model_dump_json() for r in documents]), encoding="utf-8")
    services_path.write_text("\n".join([r.model_dump_json() for r in services]), encoding="utf-8")
    deployments_path.write_text("\n".join([r.model_dump_json() for r in deployments]), encoding="utf-8")
    logs_path.write_text("\n".join([r.model_dump_json() for r in logs]), encoding="utf-8")
    metrics_path.write_text("\n".join([r.model_dump_json() for r in metrics]), encoding="utf-8")

    return {
        "incidents": incidents_path,
        "documents": docs_path,
        "services": services_path,
        "deployments": deployments_path,
        "logs": logs_path,
        "metrics": metrics_path,
    }
