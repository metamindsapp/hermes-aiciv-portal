"""AiCIV workspace backend for the Hermes dashboard plugin.

Mounted by Hermes at ``/api/plugins/aiciv-workspace/``.  This module owns only
AiCIV product state and bridges to Presence.  Hermes remains authoritative for
Hermes sessions/tools/skills/cron/etc; Presence remains authoritative for
Presence jobs/results/receipts.

Security invariants:
- Hermes' dashboard auth gate protects every route in this router.
- Provider/gateway secrets are server-side only.
- Browser-supplied participant/continuity identity is ignored.
- Presence success/cancellation state is never inferred from HTTP delivery.
- Local writes use atomic replacement and chmod 0600 where supported.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_JOB_ID_RE = re.compile(r"^job_[a-f0-9]{24}$")
_PROJECT_ID_RE = re.compile(r"^prj_[a-f0-9]{24}$")
_REF_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}:[^\s]{1,500}$")
_ALLOWED_PROJECT_STATUS = {"active", "paused", "completed", "archived"}
_STATE_LOCK = threading.Lock()
_STATE_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_path() -> Path:
    configured = os.environ.get("AICIV_HERMES_STATE_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".hermes" / "aiciv" / "workspace.json"


def _empty_state() -> dict[str, Any]:
    return {
        "version": _STATE_VERSION,
        "projects": {},
        "references": {},
        "activity": [],
    }


def _read_state_unlocked() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return _empty_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(payload, dict):
        return _empty_state()
    payload.setdefault("version", _STATE_VERSION)
    payload.setdefault("projects", {})
    payload.setdefault("references", {})
    payload.setdefault("activity", [])
    if not isinstance(payload["projects"], dict):
        payload["projects"] = {}
    if not isinstance(payload["references"], dict):
        payload["references"] = {}
    if not isinstance(payload["activity"], list):
        payload["activity"] = []
    return payload


def _write_state_unlocked(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _activity_unlocked(
    state: dict[str, Any],
    *,
    kind: str,
    object_ref: str,
    summary: str,
    actor: str = "human",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": f"evt_{secrets.token_hex(12)}",
        "kind": kind[:120],
        "objectRef": object_ref[:560],
        "summary": summary[:1000],
        "actor": actor[:80],
        "createdAt": _now(),
    }
    if metadata:
        event["metadata"] = metadata
    state["activity"].append(event)
    state["activity"] = state["activity"][-5000:]
    return event


def _clean_text(value: Any, *, limit: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError("must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError("required")
    if len(value) > limit:
        raise ValueError("too long")
    return value


def _canonical_ref(kind: str, object_id: str) -> str:
    ref = f"{kind.strip().lower()}:{object_id.strip()}"
    if not _REF_RE.fullmatch(ref):
        raise ValueError("invalid object reference")
    return ref


def _presence_config() -> tuple[str, str]:
    return (
        os.environ.get("PRESENCE_GATEWAY_URL", "").strip().rstrip("/"),
        os.environ.get("PRESENCE_GATEWAY_API_KEY", "").strip(),
    )


class PresenceUnavailable(Exception):
    def __init__(self, status: int | None = None):
        super().__init__("presence unavailable")
        self.status = status


async def _presence_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    auth: bool = True,
) -> dict[str, Any]:
    base, key = _presence_config()
    if not base or (auth and not key):
        raise PresenceUnavailable()

    def perform() -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {key}"
        req = UrlRequest(f"{base}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=8) as response:  # noqa: S310 - URL is server config, not user input
                raw = response.read(2_000_000)
        except HTTPError as exc:
            # Intentionally do not forward the provider/gateway body.
            raise PresenceUnavailable(exc.code) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise PresenceUnavailable() from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PresenceUnavailable() from exc
        if not isinstance(parsed, dict):
            raise PresenceUnavailable()
        return parsed

    return await asyncio.to_thread(perform)


def _presence_error(exc: PresenceUnavailable) -> JSONResponse:
    if exc.status == 404:
        return JSONResponse({"error": "presence_job_not_found"}, status_code=404)
    if exc.status == 409:
        return JSONResponse({"error": "presence_job_conflict"}, status_code=409)
    return JSONResponse({"error": "presence_unavailable"}, status_code=502)


@router.get("/meta")
async def meta() -> dict[str, Any]:
    base, key = _presence_config()
    return {
        "product": "AiCIV",
        "direction": "The Living Record",
        "brandVersion": "2026-08-08.v1",
        "presenceConfigured": bool(base and key),
        "civName": os.environ.get("AICIV_CIV_NAME", "").strip() or None,
        "humanName": os.environ.get("AICIV_HUMAN_NAME", "").strip() or None,
        "disclosure": "Outputs are AI-generated. Verify before acting. (EU AI Act, Art. 50)",
    }


@router.get("/presence/ready")
async def presence_ready() -> JSONResponse:
    try:
        payload = await _presence_json("GET", "/readyz", auth=False)
    except PresenceUnavailable as exc:
        return _presence_error(exc)
    return JSONResponse({
        "ready": bool(payload.get("ready")),
        "activeVoiceSessions": payload.get("activeVoiceSessions"),
        "transport": payload.get("aicivTransport"),
        "durableDelegation": payload.get("durableDelegation"),
    })


@router.post("/presence/voice-token")
async def voice_token(_: Request) -> JSONResponse:
    civ = os.environ.get("AICIV_CIV_NAME", "").strip()
    human = os.environ.get("AICIV_HUMAN_NAME", "").strip()
    if not civ or not human:
        return JSONResponse({"error": "aiciv_identity_not_configured"}, status_code=503)
    try:
        payload = await _presence_json(
            "POST",
            "/v1/voice/token",
            payload={
                "participantName": f"{civ}:{human}:hermes-web"[:160],
                "continuityKey": f"{civ}:{human}"[:160],
                "surface": "hermes-web",
            },
        )
    except PresenceUnavailable as exc:
        return _presence_error(exc)
    token = payload.get("token")
    conversation_id = payload.get("conversationId")
    if not isinstance(token, str) or not token or not isinstance(conversation_id, str) or not conversation_id:
        return JSONResponse({"error": "invalid_presence_token_response"}, status_code=502)
    return JSONResponse({"token": token, "conversationId": conversation_id})


@router.get("/jobs")
async def jobs(limit: int = 50, status: str | None = None) -> JSONResponse:
    limit = max(1, min(int(limit), 100))
    query = {"limit": str(limit)}
    if status:
        query["status"] = status
    try:
        payload = await _presence_json("GET", f"/v1/delegations?{urlencode(query)}")
    except PresenceUnavailable as exc:
        return _presence_error(exc)
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list):
        return JSONResponse({"error": "invalid_presence_jobs_response"}, status_code=502)
    return JSONResponse({"jobs": raw_jobs[:limit], "count": min(len(raw_jobs), limit)})


@router.get("/jobs/{job_id}")
async def job(job_id: str) -> JSONResponse:
    if not _JOB_ID_RE.fullmatch(job_id):
        return JSONResponse({"error": "invalid_job_id"}, status_code=400)
    try:
        payload = await _presence_json("GET", f"/v1/delegations/{job_id}")
    except PresenceUnavailable as exc:
        return _presence_error(exc)
    if not isinstance(payload.get("job"), dict):
        return JSONResponse({"error": "invalid_presence_job_response"}, status_code=502)
    return JSONResponse({"job": payload["job"]})


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> JSONResponse:
    if not _JOB_ID_RE.fullmatch(job_id):
        return JSONResponse({"error": "invalid_job_id"}, status_code=400)
    try:
        payload = await _presence_json("POST", f"/v1/delegations/{job_id}/cancel", payload={})
    except PresenceUnavailable as exc:
        return _presence_error(exc)
    current = payload.get("job")
    if not isinstance(current, dict):
        return JSONResponse({"error": "invalid_presence_job_response"}, status_code=502)
    # 202 is deliberate: this proves the request was accepted, not cancellation completion.
    return JSONResponse({"job": current, "semanticReceipt": "cancel_requested_not_cancelled"}, status_code=202)


@router.get("/projects")
async def list_projects() -> dict[str, Any]:
    with _STATE_LOCK:
        state = _read_state_unlocked()
        projects = list(state["projects"].values())
    projects.sort(key=lambda item: item.get("updatedAt", ""), reverse=True)
    return {"projects": projects, "count": len(projects)}


@router.post("/projects")
async def create_project(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        title = _clean_text(body.get("title"), limit=240, required=True)
        goal = _clean_text(body.get("goal"), limit=8000, required=True)
        summary = _clean_text(body.get("summary", ""), limit=12000)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JSONResponse({"error": "invalid_project", "detail": str(exc)}, status_code=400)

    now = _now()
    with _STATE_LOCK:
        state = _read_state_unlocked()
        project_id = f"prj_{secrets.token_hex(12)}"
        project = {
            "projectId": project_id,
            "title": title,
            "goal": goal,
            "summary": summary,
            "status": "active",
            "links": [],
            "createdAt": now,
            "updatedAt": now,
        }
        state["projects"][project_id] = project
        _activity_unlocked(
            state,
            kind="project.created",
            object_ref=f"project:{project_id}",
            summary=f"Created project {title}",
        )
        _write_state_unlocked(state)
    return JSONResponse({"project": project}, status_code=201)


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, request: Request) -> JSONResponse:
    if not _PROJECT_ID_RE.fullmatch(project_id):
        return JSONResponse({"error": "invalid_project_id"}, status_code=400)
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid body")
    except (ValueError, json.JSONDecodeError):
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    with _STATE_LOCK:
        state = _read_state_unlocked()
        project = state["projects"].get(project_id)
        if not isinstance(project, dict):
            return JSONResponse({"error": "project_not_found"}, status_code=404)
        try:
            if "title" in body:
                project["title"] = _clean_text(body["title"], limit=240, required=True)
            if "goal" in body:
                project["goal"] = _clean_text(body["goal"], limit=8000, required=True)
            if "summary" in body:
                project["summary"] = _clean_text(body["summary"], limit=12000)
            if "status" in body:
                status = _clean_text(body["status"], limit=40, required=True)
                if status not in _ALLOWED_PROJECT_STATUS:
                    raise ValueError("invalid status")
                project["status"] = status
        except ValueError as exc:
            return JSONResponse({"error": "invalid_project", "detail": str(exc)}, status_code=400)
        project["updatedAt"] = _now()
        _activity_unlocked(
            state,
            kind="project.updated",
            object_ref=f"project:{project_id}",
            summary=f"Updated project {project.get('title', project_id)}",
        )
        _write_state_unlocked(state)
        result = dict(project)
    return JSONResponse({"project": result})


@router.post("/projects/{project_id}/links")
async def add_project_link(project_id: str, request: Request) -> JSONResponse:
    if not _PROJECT_ID_RE.fullmatch(project_id):
        return JSONResponse({"error": "invalid_project_id"}, status_code=400)
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        kind = _clean_text(body.get("kind"), limit=40, required=True).lower()
        object_id = _clean_text(body.get("objectId"), limit=500, required=True)
        relation = _clean_text(body.get("relation", "related"), limit=100, required=True)
        object_ref = _canonical_ref(kind, object_id)
    except (ValueError, json.JSONDecodeError) as exc:
        return JSONResponse({"error": "invalid_link", "detail": str(exc)}, status_code=400)

    with _STATE_LOCK:
        state = _read_state_unlocked()
        project = state["projects"].get(project_id)
        if not isinstance(project, dict):
            return JSONResponse({"error": "project_not_found"}, status_code=404)
        link = {"kind": kind, "objectId": object_id, "relation": relation, "addedAt": _now()}
        exists = any(
            isinstance(item, dict)
            and item.get("kind") == kind
            and item.get("objectId") == object_id
            and item.get("relation") == relation
            for item in project.setdefault("links", [])
        )
        if not exists:
            project["links"].append(link)
            project["updatedAt"] = _now()
            _activity_unlocked(
                state,
                kind="project.linked",
                object_ref=object_ref,
                summary=f"Linked {object_ref} to {project.get('title', project_id)}",
                metadata={"projectId": project_id, "relation": relation},
            )
            _write_state_unlocked(state)
    return JSONResponse({"project": project, "created": not exists}, status_code=201 if not exists else 200)


@router.get("/activity")
async def activity(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    with _STATE_LOCK:
        events = list(_read_state_unlocked()["activity"])
    events.reverse()
    return {"events": events[:limit], "count": min(len(events), limit)}


@router.get("/references")
async def list_references() -> dict[str, Any]:
    with _STATE_LOCK:
        refs = list(_read_state_unlocked()["references"].values())
    refs.sort(key=lambda item: item.get("savedAt", ""), reverse=True)
    return {"references": refs, "count": len(refs)}


@router.post("/references")
async def save_reference(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        kind = _clean_text(body.get("kind"), limit=40, required=True).lower()
        object_id = _clean_text(body.get("objectId"), limit=500, required=True)
        object_ref = _canonical_ref(kind, object_id)
        label = _clean_text(body.get("label", object_ref), limit=500, required=True)
        note = _clean_text(body.get("note", ""), limit=4000)
    except (ValueError, json.JSONDecodeError) as exc:
        return JSONResponse({"error": "invalid_reference", "detail": str(exc)}, status_code=400)

    item = {"ref": object_ref, "kind": kind, "objectId": object_id, "label": label, "note": note, "savedAt": _now()}
    with _STATE_LOCK:
        state = _read_state_unlocked()
        state["references"][object_ref] = item
        _activity_unlocked(
            state,
            kind="reference.saved",
            object_ref=object_ref,
            summary=f"Saved reference {label}",
        )
        _write_state_unlocked(state)
    return JSONResponse({"reference": item, "semanticReceipt": "shared_reference_saved"}, status_code=201)


@router.delete("/references/{kind}/{object_id:path}")
async def remove_reference(kind: str, object_id: str) -> JSONResponse:
    try:
        object_ref = _canonical_ref(kind, object_id)
    except ValueError:
        return JSONResponse({"error": "invalid_reference"}, status_code=400)
    with _STATE_LOCK:
        state = _read_state_unlocked()
        removed = state["references"].pop(object_ref, None) is not None
        if removed:
            _activity_unlocked(
                state,
                kind="reference.removed",
                object_ref=object_ref,
                summary=f"Removed reference {object_ref}",
            )
            _write_state_unlocked(state)
    return JSONResponse({"ref": object_ref, "removed": removed})
