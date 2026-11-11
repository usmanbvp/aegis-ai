from __future__ import annotations

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ServiceEntity(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="production")
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class DeploymentEntity(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deployment_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration_changes: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class IncidentEntity(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ground_truth_root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    relevant_document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expected_log_patterns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expected_metric_patterns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    deployment: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    expected_evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class ApprovalEntity(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    approval_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(60), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(60), nullable=False)


class DocumentEntity(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[str] = mapped_column(String(60), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class LogEntryEntity(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(120), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(120), nullable=False)


class MetricSampleEntity(Base):
    __tablename__ = "metric_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(120), nullable=False)
