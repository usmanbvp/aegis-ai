from pathlib import Path

from app.database import initialize_database, seed_database
from app.database.approvals import get_incident_history, save_incident_approval


def test_database_can_initialize_and_seed(tmp_path: Path) -> None:
    db_path = tmp_path / "aegis_test.db"
    session = initialize_database(f"sqlite:///{db_path}")

    stats = seed_database(session=session)

    assert stats["incidents"] >= 1
    assert stats["documents"] >= 1
    assert stats["services"] >= 1
    assert stats["deployments"] >= 1
    assert stats["logs"] >= 1
    assert stats["metrics"] >= 1


def test_incident_approval_is_persisted(tmp_path: Path) -> None:
    db_path = tmp_path / "aegis_approval_test.db"
    session = initialize_database(f"sqlite:///{db_path}")
    seed_database(session=session)

    approval = save_incident_approval(session, incident_id="INC-001", decision="approve")

    assert approval.decision == "approve"
    assert approval.incident_id == "INC-001"
    assert approval.status == "approved"


def test_incident_history_is_queryable(tmp_path: Path) -> None:
    db_path = tmp_path / "aegis_history_test.db"
    session = initialize_database(f"sqlite:///{db_path}")
    seed_database(session=session)
    save_incident_approval(session, incident_id="INC-001", decision="approve")

    history = get_incident_history(session, incident_id="INC-001")

    assert len(history) >= 1
    assert history[0]["incident_id"] == "INC-001"
    assert history[0]["decision"] == "approve"
