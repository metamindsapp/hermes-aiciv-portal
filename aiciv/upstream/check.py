#!/usr/bin/env python3
"""Small upstream-sync helper for a local checkout.

Run inside a real git checkout with network access. It never mutates the branch;
it fetches the configured upstream and prints exactly how far the product pin is
behind/ahead plus changed paths. Sync itself remains an explicit reviewed PR.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_DOC = ROOT / ".aiciv" / "UPSTREAM.md"
UPSTREAM_URL = "https://github.com/NousResearch/hermes-agent.git"
REMOTE = "hermes-upstream"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def main() -> int:
    text = UPSTREAM_DOC.read_text(encoding="utf-8")
    match = re.search(r"Pinned commit:\s*`([0-9a-f]{40})`", text)
    if not match:
        raise SystemExit("could not parse pinned Hermes SHA from .aiciv/UPSTREAM.md")
    pinned = match.group(1)

    try:
        git("remote", "get-url", REMOTE)
    except subprocess.CalledProcessError:
        git("remote", "add", REMOTE, UPSTREAM_URL)

    git("fetch", REMOTE, "main")
    latest = git("rev-parse", f"{REMOTE}/main")
    behind = git("rev-list", "--count", f"{pinned}..{latest}")
    ahead = git("rev-list", "--count", f"{latest}..{pinned}")

    print(f"pinned : {pinned}")
    print(f"latest : {latest}")
    print(f"behind : {behind}")
    print(f"ahead  : {ahead}")

    if latest == pinned:
        print("AiCIV Hermes baseline is current.")
        return 0

    print("\nChanged paths since the pin:")
    print(git("diff", "--name-status", f"{pinned}..{latest}"))
    print("\nDo not merge this automatically. Create an upstream-sync branch and update .aiciv/UPSTREAM.md in the same reviewed change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
