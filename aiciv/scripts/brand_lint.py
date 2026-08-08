#!/usr/bin/env python3
"""Fail CI when the branded dashboard violates machine-checkable hard rules."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / "brand" / "themes" / "aiciv-living-record.yaml"
PLUGIN = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "dashboard"
JS = PLUGIN / "dist" / "index.js"
CSS = PLUGIN / "dist" / "aiciv.css"
MANIFEST = PLUGIN / "manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("brand lint failed: " + message)


def main() -> int:
    theme = THEME.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    require(manifest.get("name") == "aiciv-workspace", "unexpected plugin identity")
    require(manifest.get("tab", {}).get("override") == "/", "AiCIV Now must own the root page")

    for token in ("#201e1d", "#f3f2f2", "#d6006c", "#0088b0", "Source Serif 4"):
        require(token in theme, f"theme missing constitutional token {token}")

    require(
        re.search(r"(?:linear|radial|conic)-gradient\s*\(", theme, flags=re.I) is None,
        "theme contains a gradient",
    )

    require("aiciv-dateline-rail" in js and "aiciv-dateline-rail__live" in js, "dateline rail missing")
    require("active_sessions" in js, "live rail is not tied to runtime state")
    require("#d6006c" in css and ".aiciv-dateline-rail__live" in css, "live Magenta rule missing")

    disclosure = "Outputs are AI-generated. Verify before acting. (EU AI Act, Art. 50)"
    require(disclosure in js, "required public disclosure missing")

    banned_copy = (
        "revolutionary",
        "game-changing",
        "unlock unprecedented",
        "seamless",
        "cutting-edge",
        "in today's fast-paced world",
        "it's not just",
        "powered by AiCIV",
    )
    visible_product = js.lower()
    for phrase in banned_copy:
        require(phrase.lower() not in visible_product, f"banned brand copy found: {phrase}")

    # Product chrome must not contain emoji pictographs. The dateline's BLACK
    # CIRCLE (U+25CF) is intentional and is outside these emoji blocks.
    emoji = re.compile(
        "["
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "]"
    )
    require(emoji.search(js + css) is None, "emoji pictograph found in product chrome")

    require("Talk Live" in js, "global Presence control missing")
    require("cancel_requested_not_cancelled" in (PLUGIN / "plugin_api.py").read_text(encoding="utf-8"), "two-phase cancellation semantic receipt missing")
    require("continuityKey" in (PLUGIN / "plugin_api.py").read_text(encoding="utf-8"), "multi-body continuity key missing")

    print("AiCIV brand lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
