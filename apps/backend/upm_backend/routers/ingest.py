"""Ingestion UI backend (§1.1 Option B + §1.2): CSV upload, schema inference, preview.

Uploaded files land under settings.upload_dir (a shared volume in Compose) so the worker
can read them when the job runs. Inference is shown to the user for review before load.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from upm_control_plane.models import Upload
from upm_shared.inference import InferredSchema, UploadOut

from upm_backend.audit import record_audit
from upm_backend.config import Settings, get_settings
from upm_backend.db import get_session
from upm_backend.deps import UserContext, require_cap

router = APIRouter(tags=["ingest"], prefix="/ingest")

_TABLE_RE = re.compile(r"[^a-z0-9_]+")


def _suggested_table(filename: str) -> str:
    stem = Path(filename).stem.lower()
    name = _TABLE_RE.sub("_", stem).strip("_") or "dataset"
    if name[0].isdigit():
        name = f"t_{name}"
    return name[:120]


def _out(up: Upload) -> UploadOut:
    return UploadOut(
        id=up.id,
        original_filename=up.original_filename,
        suggested_table=up.suggested_table or "dataset",
        schema_=InferredSchema.model_validate(up.inferred_schema),
        created_at=up.created_at,
    )


@router.post("/uploads", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadOut:
    if not (file.filename or "").lower().endswith((".csv", ".txt", ".tsv")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "only .csv/.tsv/.txt files are supported")

    upload_id = str(uuid.uuid4())
    dest_dir = Path(settings.upload_dir) / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(file.filename).name

    limit = settings.max_upload_mb * 1024 * 1024
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"file exceeds {settings.max_upload_mb} MB limit",
                )
            out.write(chunk)

    from upm_ingestion.inference import infer_csv

    try:
        inferred = infer_csv(str(dest))
    except Exception as e:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"could not parse CSV: {e}")

    up = Upload(
        id=upload_id,
        original_filename=Path(file.filename).name,
        stored_path=str(dest),
        kind="csv",
        delimiter=inferred.delimiter,
        has_header=bool(inferred.has_header) if inferred.has_header is not None else True,
        row_estimate=inferred.row_estimate,
        inferred_schema=inferred.model_dump(),
        suggested_table=_suggested_table(file.filename),
        status="ready",
        created_by=ctx.user.id,
    )
    session.add(up)
    session.flush()
    record_audit(session, actor_id=ctx.user.id, action="upload", entity_type="upload",
                 entity_id=up.id, after={"filename": up.original_filename, "rows": up.row_estimate})
    return _out(up)


@router.get("/uploads", response_model=list[UploadOut])
def list_uploads(
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> list[UploadOut]:
    return [_out(u) for u in session.query(Upload).order_by(Upload.created_at.desc()).all()]


@router.get("/uploads/{upload_id}", response_model=UploadOut)
def get_upload(
    upload_id: str,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> UploadOut:
    up = session.get(Upload, upload_id)
    if up is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "upload not found")
    return _out(up)


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: str,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> None:
    up = session.get(Upload, upload_id)
    if up is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "upload not found")
    try:
        p = Path(up.stored_path)
        p.unlink(missing_ok=True)
        if p.parent.exists():
            p.parent.rmdir()
    except OSError:
        pass
    record_audit(session, actor_id=ctx.user.id, action="delete", entity_type="upload",
                 entity_id=up.id)
    session.delete(up)
