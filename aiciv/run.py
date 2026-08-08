#!/usr/bin/env python3
"""Boot the Hermes dashboard as the AiCIV branded product.

This is the preferred local/product launcher for this distribution. It ensures
the Living Record theme and AiCIV workspace plugin are installed into the
selected Hermes home before delegating to Hermes' own dashboard command.

It does not rewrite model/provider credentials and it does not bypass Hermes
session/auth behavior.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AiCIV Hermes product dashboard")
    parser.add_argument("--hermes-home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--no-install", action="store_true", help="Skip refreshing the AiCIV theme/plugin layer")
    args, passthrough = parser.parse_known_args()

    root = Path(__file__).resolve().parents[1]
    installer = root / "aiciv" / "install.py"

    env = os.environ.copy()
    env["HERMES_HOME"] = str(args.hermes_home.expanduser().resolve())
    env.setdefault("AICIV_PRODUCT_DISTRIBUTION", "1")

    if not args.no_install:
        install = subprocess.run(
            [sys.executable, str(installer), "--hermes-home", env["HERMES_HOME"]],
            cwd=root,
            env=env,
        )
        if install.returncode != 0:
            return install.returncode

    command = [sys.executable, "-m", "hermes_cli.main", "web"]
    if args.host:
        command.extend(["--host", args.host])
    if args.port is not None:
        command.extend(["--port", str(args.port)])
    command.extend(passthrough)

    print("[AiCIV] The Living Record")
    print(f"[AiCIV] Hermes home: {env['HERMES_HOME']}")
    return subprocess.call(command, cwd=root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
