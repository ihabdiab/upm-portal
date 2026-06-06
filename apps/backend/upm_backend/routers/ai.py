"""AI proxy (Phase 5) — provider-agnostic, OpenAI-compatible, SELECT-only over DuckDB.

v1 ships the scaffold and guardrails wiring; the tool-calling loop is filled in when the
Qwen endpoint is confirmed (§13 Phase 5). Without LLM_BASE_URL this returns 503 so the
contract and route exist without pretending to have a model.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from upm_sql_tools.validate import SqlValidationError, assert_select_only

from upm_backend.config import Settings, get_settings
from upm_backend.deps import UserContext, get_services, get_user_context

router = APIRouter(tags=["ai"], prefix="/ai")


class ChatRequest(BaseModel):
    message: str
    thinking: bool = False


@router.get("/status")
def ai_status(settings: Settings = Depends(get_settings)) -> dict:
    return {"enabled": bool(settings.llm_base_url), "model": settings.llm_model}


@router.post("/sql/validate")
def validate_sql(
    body: dict,
    _: UserContext = Depends(get_user_context),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Expose the same SELECT-only guard the AI path uses (allow-list + bounded)."""
    sql = body.get("sql", "")
    try:
        assert_select_only(
            sql, dialect="duckdb", require_bounded=True,
        )
    except SqlValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"ok": True}


@router.post("/chat")
def chat(
    body: ChatRequest,
    _: UserContext = Depends(get_user_context),
    settings: Settings = Depends(get_settings),
    services=Depends(get_services),
) -> dict:
    if not settings.llm_base_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI is not configured (set UPM_LLM_BASE_URL). Phase 5 feature.",
        )
    # Placeholder: the tool-calling loop (list_tables/describe_table/run_readonly_sql/
    # propose_chart) lands once the endpoint is confirmed.
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "AI chat loop not yet implemented")
