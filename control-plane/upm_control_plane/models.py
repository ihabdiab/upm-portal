"""Control-plane ORM models (§5). PK/FK/timestamps explicit.

Two stores rule (ADR-003): this holds *metadata only*. KPI data lives in DuckDB.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from upm_control_plane.base import Base, JsonType


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = _now()

    project_roles: Mapped[list[UserProjectRole]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    capabilities: Mapped[list[RoleCapability]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class RoleCapability(Base):
    __tablename__ = "role_capabilities"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    capability_id: Mapped[int] = mapped_column(ForeignKey("capabilities.id"), primary_key=True)

    role: Mapped[Role] = relationship(back_populates="capabilities")
    capability: Mapped[Capability] = relationship()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()


class UserProjectRole(Base):
    __tablename__ = "user_project_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)

    user: Mapped[User] = relationship(back_populates="project_roles")
    project: Mapped[Project] = relationship()
    role: Mapped[Role] = relationship()


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class JobConfig(Base):
    __tablename__ = "job_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_schema: Mapped[str] = mapped_column(String(128), nullable=False)
    source_table: Mapped[str] = mapped_column(String(128), nullable=False)
    query_definition: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    target_table: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    schedule: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    load_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="upsert")
    watermark_column: Mapped[str | None] = mapped_column(String(128))
    key_columns: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    retention: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    guards: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    runs: Mapped[list[JobRun]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_config_id: Mapped[int] = mapped_column(
        ForeignKey("job_configs.id"), index=True, nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    started_at: Mapped[datetime] = _now()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watermark_before: Mapped[str | None] = mapped_column(String(255))
    watermark_after: Mapped[str | None] = mapped_column(String(255))
    landing_path: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)

    job: Mapped[JobConfig] = relationship(back_populates="runs")


class TableRegistry(Base):
    __tablename__ = "table_registry"

    table_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_job_id: Mapped[int | None] = mapped_column(ForeignKey("job_configs.id"))
    schema_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    table_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_load_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_load_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_load_status: Mapped[str | None] = mapped_column(String(16))
    last_watermark_value: Mapped[str | None] = mapped_column(String(255))
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (UniqueConstraint("id", name="uq_audit_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128))
    before: Mapped[dict | None] = mapped_column(JsonType)
    after: Mapped[dict | None] = mapped_column(JsonType)
    ts: Mapped[datetime] = _now()


class Connection(Base):
    """Saved RDBMS connection (§4). Credentials are stored encrypted, never plaintext."""

    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    host: Mapped[str | None] = mapped_column(String(255))
    port: Mapped[int | None] = mapped_column(Integer)
    database: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    encrypted_password: Mapped[str | None] = mapped_column(Text)
    encrypted_url: Mapped[str | None] = mapped_column(Text)  # for kind=generic
    extra: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Upload(Base):
    """An uploaded CSV dataset (§1.1 Option B), ready to be used as a job source."""

    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="csv")
    delimiter: Mapped[str | None] = mapped_column(String(4))
    has_header: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    row_estimate: Mapped[int | None] = mapped_column(Integer)
    inferred_schema: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    suggested_table: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()
