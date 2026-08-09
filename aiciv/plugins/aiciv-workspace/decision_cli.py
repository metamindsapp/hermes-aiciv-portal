#!/usr/bin/env python3
"""Machine-friendly CLI for AiCIV structured Decisions.

Examples:

  python decision_cli.py create \
    --title "Provider choice" \
    --question "Which provider should I promote?" \
    --option approve:"Promote candidate B" \
    --option hold:"Keep evaluating" \
    --recommendation approve \
    --evidence-ref task:t_123 \
    --idempotency-key provider-choice-2026-08-09

  python decision_cli.py list --status pending
  python decision_cli.py show dec_...

The CLI writes the same SQLite store used by the authenticated dashboard API.
It records requests and human responses only; it never executes downstream
side effects.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import decision_store as store  # noqa: E402


def _option(value: str) -> dict[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("option must be id:label")
    option_id, label = value.split(":", 1)
    option_id = option_id.strip()
    label = label.strip()
    if not option_id or not label:
        raise argparse.ArgumentTypeError("option id and label are required")
    return {"id": option_id, "label": label}


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="AiCIV structured decision tool")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create or idempotently recover a decision request")
    create.add_argument("--title", required=True)
    create.add_argument("--question", required=True)
    create.add_argument("--option", action="append", type=_option, required=True)
    create.add_argument("--recommendation")
    create.add_argument("--rationale", default="")
    create.add_argument("--evidence-ref", action="append", default=[])
    create.add_argument("--blocking-ref", action="append", default=[])
    create.add_argument("--urgency", choices=("normal", "high"), default="normal")
    create.add_argument("--idempotency-key")
    create.add_argument("--created-by", default="aiciv")

    listing = sub.add_parser("list", help="List decisions")
    listing.add_argument("--status", choices=("pending", "resolved", "withdrawn"))
    listing.add_argument("--limit", type=int, default=100)

    show = sub.add_parser("show", help="Read one decision and its response receipt")
    show.add_argument("decision_id")

    withdraw = sub.add_parser("withdraw", help="Withdraw a pending decision request")
    withdraw.add_argument("decision_id")
    withdraw.add_argument("--actor", default="aiciv")

    events = sub.add_parser("events", help="Read decision lifecycle events")
    events.add_argument("--after")
    events.add_argument("--limit", type=int, default=100)

    args = parser.parse_args()

    try:
        if args.command == "create":
            if len(args.option) < 2:
                parser.error("create requires at least two --option values")
            payload = {
                "idempotencyKey": args.idempotency_key,
                "title": args.title,
                "question": args.question,
                "options": args.option,
                "recommendation": args.recommendation,
                "rationale": args.rationale,
                "evidenceRefs": args.evidence_ref,
                "blockingRefs": args.blocking_ref,
                "urgency": args.urgency,
                "createdBy": args.created_by,
            }
            decision, created = store.create_decision(payload)
            _print({
                "decision": decision,
                "created": created,
                "semanticReceipt": "decision_request_recorded_not_human_response",
            })
            return 0

        if args.command == "list":
            values = store.list_decisions(status=args.status, limit=args.limit)
            _print({"decisions": values, "count": len(values)})
            return 0

        if args.command == "show":
            decision = store.get_decision(args.decision_id)
            if decision is None:
                _print({"error": "decision_not_found"})
                return 2
            _print({"decision": decision})
            return 0

        if args.command == "withdraw":
            _print({
                "decision": store.withdraw_decision(args.decision_id, actor=args.actor),
                "semanticReceipt": "decision_withdrawn_no_downstream_execution",
            })
            return 0

        if args.command == "events":
            values = store.list_events(after=args.after, limit=args.limit)
            _print({"events": values, "count": len(values)})
            return 0
    except (KeyError, ValueError) as exc:
        _print({"error": str(exc).strip("'")})
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
