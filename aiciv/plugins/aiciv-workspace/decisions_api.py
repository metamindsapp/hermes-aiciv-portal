"""Structured Needs You API for the AiCIV Hermes workspace."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

import decision_store as store  # noqa: E402


router = APIRouter()

_DECISION_ID_RE = re.compile(r"^dec_[a-f0-9]{24}$")
_OPTION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{8,160}$")
_REF_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}:[^\s]{1,500}$")
_URGENCIES = {"normal", "high"}
_STATUSES = {"pending", "resolved", "withdrawn"}


def _text(value: Any, *, field: str, limit: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field}_required")
    if len(value) > limit:
        raise ValueError(f"{field}_too_long")
    return value


def _refs(value: Any, *, field: str, limit: int = 50) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"invalid_{field}")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        ref = _text(raw, field=field, limit=540, required=True)
        if not _REF_RE.fullmatch(ref):
            raise ValueError(f"invalid_{field}")
        if ref not in seen:
            seen.add(ref)
            result.append(ref)
    return result


def _options(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not 2 <= len(value) <= 12:
        raise ValueError("options_must_have_2_to_12_items")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("invalid_option")
        option_id = _text(item.get("id"), field="option_id", limit=40, required=True)
        label = _text(item.get("label"), field="option_label", limit=160, required=True)
        description = _text(item.get("description", ""), field="option_description", limit=1000)
        if not _OPTION_ID_RE.fullmatch(option_id) or option_id in seen:
            raise ValueError("invalid_option_id")
        seen.add(option_id)
        option = {"id": option_id, "label": label}
        if description:
            option["description"] = description
        result.append(option)
    return result


def _validate_create(body: Any, *, created_by: str) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("invalid_body")
    options = _options(body.get("options"))
    option_ids = {item["id"] for item in options}
    recommendation = _text(body.get("recommendation", ""), field="recommendation", limit=40)
    if recommendation and recommendation not in option_ids:
        raise ValueError("recommendation_not_an_option")
    urgency = _text(body.get("urgency", "normal"), field="urgency", limit=20, required=True).lower()
    if urgency not in _URGENCIES:
        raise ValueError("invalid_urgency")
    idempotency_key = _text(body.get("idempotencyKey", ""), field="idempotency_key", limit=160)
    if idempotency_key and not _REQUEST_ID_RE.fullmatch(idempotency_key):
        raise ValueError("invalid_idempotency_key")
    return {
        "idempotencyKey": idempotency_key or None,
        "title": _text(body.get("title"), field="title", limit=240, required=True),
        "question": _text(body.get("question"), field="question", limit=4000, required=True),
        "options": options,
        "recommendation": recommendation or None,
        "rationale": _text(body.get("rationale", ""), field="rationale", limit=12000),
        "evidenceRefs": _refs(body.get("evidenceRefs"), field="evidence_refs"),
        "blockingRefs": _refs(body.get("blockingRefs"), field="blocking_refs"),
        "urgency": urgency,
        "createdBy": created_by,
    }


@router.get("/decisions")
def list_decisions(status: str | None = None, limit: int = 100) -> JSONResponse:
    if status is not None and status not in _STATUSES:
        return JSONResponse({"error": "invalid_decision_status"}, status_code=400)
    decisions = store.list_decisions(status=status, limit=limit)
    return JSONResponse({"decisions": decisions, "count": len(decisions)})


@router.get("/decisions/events")
def decision_events(after: str | None = None, limit: int = 100) -> JSONResponse:
    events = store.list_events(after=after, limit=limit)
    return JSONResponse({"events": events, "count": len(events)})


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str) -> JSONResponse:
    if not _DECISION_ID_RE.fullmatch(decision_id):
        return JSONResponse({"error": "invalid_decision_id"}, status_code=400)
    decision = store.get_decision(decision_id)
    if decision is None:
        return JSONResponse({"error": "decision_not_found"}, status_code=404)
    return JSONResponse({"decision": decision})


@router.post("/decisions")
async def create_decision(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        payload = _validate_create(body, created_by="dashboard")
        decision, created = store.create_decision(payload)
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code == "idempotency_conflict" else 400
        return JSONResponse({"error": code}, status_code=status)
    return JSONResponse(
        {
            "decision": decision,
            "created": created,
            "semanticReceipt": "decision_request_recorded_not_human_response",
        },
        status_code=201 if created else 200,
    )


@router.post("/decisions/{decision_id}/respond")
async def respond_decision(decision_id: str, request: Request) -> JSONResponse:
    if not _DECISION_ID_RE.fullmatch(decision_id):
        return JSONResponse({"error": "invalid_decision_id"}, status_code=400)
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid_body")
        option_id = _text(body.get("optionId"), field="option_id", limit=40, required=True)
        request_id = _text(body.get("requestId"), field="request_id", limit=160, required=True)
        note = _text(body.get("note", ""), field="note", limit=8000)
        if not _OPTION_ID_RE.fullmatch(option_id):
            raise ValueError("invalid_option_id")
        if not _REQUEST_ID_RE.fullmatch(request_id):
            raise ValueError("invalid_request_id")
        decision, recorded = store.respond_decision(
            decision_id,
            option_id=option_id,
            note=note,
            request_id=request_id,
            actor="human",
        )
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    except KeyError:
        return JSONResponse({"error": "decision_not_found"}, status_code=404)
    except ValueError as exc:
        code = str(exc)
        status = 409 if code in {
            "decision_not_pending",
            "response_idempotency_conflict",
        } else 400
        return JSONResponse({"error": code}, status_code=status)

    return JSONResponse({
        "decision": decision,
        "recorded": recorded,
        "receipt": decision.get("response"),
        "semanticReceipt": "human_decision_recorded_not_downstream_execution",
    })


@router.post("/decisions/{decision_id}/withdraw")
def withdraw_decision(decision_id: str) -> JSONResponse:
    if not _DECISION_ID_RE.fullmatch(decision_id):
        return JSONResponse({"error": "invalid_decision_id"}, status_code=400)
    try:
        decision = store.withdraw_decision(decision_id, actor="dashboard")
    except KeyError:
        return JSONResponse({"error": "decision_not_found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    return JSONResponse({
        "decision": decision,
        "semanticReceipt": "decision_withdrawn_no_downstream_execution",
    })
