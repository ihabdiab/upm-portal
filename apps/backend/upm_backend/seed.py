"""Idempotent demo seed: users, roles, a project, two jobs, and a dashboard.

Gives the Phase-1 walkthrough something to log into and look at. Safe to run repeatedly.
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from upm_control_plane.bootstrap import seed_rbac
from upm_control_plane.models import (
    Dashboard,
    JobConfig,
    Project,
    Role,
    TableRegistry,
    User,
    UserProjectRole,
)
from upm_shared.enums import LoadMode, SourceMode
from upm_shared.jobs import JobDefinition, JobSource, Retention, Schedule, Watermark

from upm_backend.jobmap import definition_to_kwargs
from upm_backend.security import hash_password

DEMO_USERS = [
    ("admin@upm.com", "admin12345", "Platform Admin", "Admin"),
    ("builder@upm.com", "builder12345", "KPI Builder", "Builder"),
    ("viewer@upm.com", "viewer12345", "KPI Viewer", "Viewer"),
]

PROJECT_NAME = "SON KPIs"


def _cs_job() -> JobDefinition:
    return JobDefinition(
        name="load_hybrid_cs_cell",
        source=JobSource(
            schema="SON",
            table="hybrid_cs_cell",
            mode=SourceMode.STRUCTURED,
            columns=["timestamp", "cell_id", "region", "traffic_erl", "drop_rate"],
        ),
        target_table="hybrid_cs_cell",
        schedule=Schedule(every="1h"),
        load_mode=LoadMode.FULL,
    )


def _ps_job() -> JobDefinition:
    return JobDefinition(
        name="load_hybrid_ps_cell",
        source=JobSource(
            schema="SON",
            table="hybrid_ps_cell",
            mode=SourceMode.STRUCTURED,
            columns=["timestamp", "cell_id", "region", "throughput_mbps", "latency_ms"],
        ),
        target_table="hybrid_ps_cell",
        schedule=Schedule(every="1h"),
        load_mode=LoadMode.UPSERT,
        watermark=Watermark(column="timestamp", type="timestamp"),
        key_columns=["cell_id", "timestamp"],
        retention=Retention(window_days=395),
    )


def _dashboard_def() -> dict:
    return {
        "version": 1,
        "layout": {"cols": 12, "rowHeight": 40},
        "widgets": [
            {
                "id": "kpi_traffic",
                "type": "kpi",
                "title": "Avg CS traffic (Erl)",
                "source": {"table": "hybrid_cs_cell"},
                "query": {
                    "table": "hybrid_cs_cell",
                    "aggregations": [{"fn": "avg", "col": "traffic_erl", "as": "value"}],
                },
                "viz": {"value": "value", "unit": "Erl", "precision": 2},
                "grid": {"x": 0, "y": 0, "w": 3, "h": 3},
            },
            {
                "id": "kpi_drop",
                "type": "kpi",
                "title": "Avg drop rate (%)",
                "source": {"table": "hybrid_cs_cell"},
                "query": {
                    "table": "hybrid_cs_cell",
                    "aggregations": [{"fn": "avg", "col": "drop_rate", "as": "value"}],
                },
                "viz": {"value": "value", "unit": "%", "precision": 3},
                "grid": {"x": 3, "y": 0, "w": 3, "h": 3},
            },
            {
                "id": "line_traffic",
                "type": "line",
                "title": "CS traffic over time by region",
                "source": {"table": "hybrid_cs_cell"},
                "query": {
                    "table": "hybrid_cs_cell",
                    "aggregations": [{"fn": "avg", "col": "traffic_erl", "as": "traffic"}],
                    "groupBy": ["timestamp", "region"],
                    "sort": [{"col": "timestamp", "dir": "asc"}],
                    "limit": 5000,
                },
                "viz": {"x": "timestamp", "series": "region", "y": "traffic"},
                "grid": {"x": 0, "y": 3, "w": 12, "h": 6},
            },
            {
                "id": "bar_drop_region",
                "type": "bar",
                "title": "Avg drop rate by region",
                "source": {"table": "hybrid_cs_cell"},
                "query": {
                    "table": "hybrid_cs_cell",
                    "aggregations": [{"fn": "avg", "col": "drop_rate", "as": "drop_rate"}],
                    "groupBy": ["region"],
                    "sort": [{"col": "region", "dir": "asc"}],
                },
                "viz": {"x": "region", "y": "drop_rate"},
                "grid": {"x": 0, "y": 9, "w": 6, "h": 6},
            },
            {
                "id": "line_throughput",
                "type": "line",
                "title": "PS throughput over time by region",
                "source": {"table": "hybrid_ps_cell"},
                "query": {
                    "table": "hybrid_ps_cell",
                    "aggregations": [{"fn": "avg", "col": "throughput_mbps", "as": "throughput"}],
                    "groupBy": ["timestamp", "region"],
                    "sort": [{"col": "timestamp", "dir": "asc"}],
                    "limit": 5000,
                },
                "viz": {"x": "timestamp", "series": "region", "y": "throughput"},
                "grid": {"x": 6, "y": 9, "w": 6, "h": 6},
            },
        ],
    }


def _get_or_create_user(session: Session, email: str, password: str, full_name: str) -> User:
    u = session.query(User).filter(User.email == email).one_or_none()
    if u is None:
        u = User(email=email, hashed_password=hash_password(password), full_name=full_name)
        session.add(u)
        session.flush()
    return u


def _assign_role(session: Session, user: User, project: Project, role_name: str) -> None:
    role = session.query(Role).filter(Role.name == role_name).one()
    if session.get(UserProjectRole, (user.id, project.id, role.id)) is None:
        session.add(UserProjectRole(user_id=user.id, project_id=project.id, role_id=role.id))


def _ensure_job(session: Session, jd: JobDefinition, created_by: int) -> JobConfig:
    row = session.query(JobConfig).filter(JobConfig.name == jd.name).one_or_none()
    if row is None:
        row = JobConfig(**definition_to_kwargs(jd, created_by=created_by), created_by=created_by)
        session.add(row)
        session.flush()
    if session.get(TableRegistry, jd.target_table) is None:
        session.add(
            TableRegistry(table_name=jd.target_table, source_job_id=row.id, is_visible=False)
        )
    return row


def seed_users_and_project(session: Session) -> tuple[dict[str, User], Project]:
    """Create the demo users, project, and role assignments. Idempotent. Shared by the
    synthetic demo and the real-CS-data flow."""
    seed_rbac(session)

    users: dict[str, User] = {}
    for email, pw, name, _role in DEMO_USERS:
        users[email] = _get_or_create_user(session, email, pw, name)

    project = session.query(Project).filter(Project.name == PROJECT_NAME).one_or_none()
    if project is None:
        project = Project(
            name=PROJECT_NAME,
            description="Demo project — Hybrid CS/PS cell KPIs from SON.",
            created_by=users["admin@upm.com"].id,
        )
        session.add(project)
        session.flush()

    for email, _pw, _name, role_name in DEMO_USERS:
        _assign_role(session, users[email], project, role_name)
    return users, project


def seed_demo(session: Session) -> dict:
    users, project = seed_users_and_project(session)

    admin_id = users["admin@upm.com"].id
    _ensure_job(session, _cs_job(), created_by=admin_id)
    _ensure_job(session, _ps_job(), created_by=admin_id)

    dash = (
        session.query(Dashboard)
        .filter(Dashboard.project_id == project.id, Dashboard.name == "Hybrid Cell Overview")
        .one_or_none()
    )
    if dash is None:
        session.add(
            Dashboard(
                project_id=project.id,
                name="Hybrid Cell Overview",
                definition=_dashboard_def(),
                version=1,
                created_by=admin_id,
            )
        )

    return {
        "project": PROJECT_NAME,
        "users": [{"email": e, "password": p, "role": r} for e, p, _n, r in DEMO_USERS],
        "jobs": ["load_hybrid_cs_cell", "load_hybrid_ps_cell"],
    }
