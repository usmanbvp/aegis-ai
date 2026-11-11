import pytest
from fastapi.testclient import TestClient

from app.agents.workflow import InvestigationWorkflow
from app.api.routes.investigation import get_investigation_workflow
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_deterministic_test_workflow():
    app.dependency_overrides[get_investigation_workflow] = lambda: InvestigationWorkflow(
        use_configured_llm=False
    )
    yield
    app.dependency_overrides.pop(get_investigation_workflow, None)


def test_investigation_history_endpoint_returns_history() -> None:
    analyze_response = client.post(
        "/api/v1/investigations/analyze", json={"incident_id": "INC-001"}
    )
    assert analyze_response.status_code == 200

    approve_response = client.post(
        "/api/v1/investigations/approve",
        json={"incident_id": "INC-001", "decision": "approve"},
    )
    assert approve_response.status_code == 200

    history_response = client.get("/api/v1/investigations/history/INC-001")
    assert history_response.status_code == 200
    payload = history_response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert payload[0]["incident_id"] == "INC-001"


def test_investigation_incident_catalog_is_listable() -> None:
    response = client.get("/api/v1/investigations/incidents")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert payload[0]["incident_id"]


def test_investigation_incident_detail_is_fetchable() -> None:
    response = client.get("/api/v1/investigations/INC-001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-001"
    assert payload["service"] == "checkout-api"
    assert "ground_truth_root_cause" not in payload
    assert "expected_evidence" not in payload
