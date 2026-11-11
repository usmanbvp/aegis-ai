from app.synthetic_data import build_deployments, build_document_corpus, build_incidents, build_logs, build_metrics, build_service_catalog


def test_incident_generation_count() -> None:
    incidents = build_incidents()
    assert len(incidents) == 50


def test_incident_has_ground_truth_and_metadata() -> None:
    incidents = build_incidents()
    incident = incidents[0]
    assert incident.ground_truth_root_cause
    assert incident.service
    assert incident.expected_evidence
    assert incident.relevant_document_ids


def test_document_generation_count() -> None:
    documents = build_document_corpus()
    assert len(documents) >= 30


def test_service_and_deployment_catalogs_exist() -> None:
    services = build_service_catalog()
    deployments = build_deployments()
    assert len(services) >= 10
    assert len(deployments) >= 20


def test_logs_and_metrics_generation_exist() -> None:
    logs = build_logs()
    metrics = build_metrics()
    assert len(logs) >= 100
    assert len(metrics) >= 200
