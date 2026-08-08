#!/usr/bin/env python3
"""Install the AiCIV branded dashboard layer into a Hermes home directory.

This does not modify provider/API credentials. Existing plugin/theme copies are
backed up before replacement. The installer also selects the Living Record theme
in config.yaml when PyYAML is available (Hermes normally provides it).
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup(path: Path, *, dry_run: bool) -> None:
    if not path.exists():
        return
    target = path.with_name(path.name + ".bak." + stamp())
    print(f"backup: {path} -> {target}")
    if not dry_run:
        shutil.move(str(path), str(target))


def copy_tree(source: Path, target: Path, *, dry_run: bool) -> None:
    backup(target, dry_run=dry_run)
    print(f"install: {source} -> {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


def copy_file(source: Path, target: Path, *, dry_run: bool) -> None:
    if target.exists():
        backup(target, dry_run=dry_run)
    print(f"install: {source} -> {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def select_theme(config_path: Path, *, dry_run: bool) -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("theme selection skipped: PyYAML unavailable; select 'AiCIV — The Living Record' in the dashboard once")
        return

    data = {}
    if config_path.exists():
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception as exc:
            print(f"theme selection skipped: could not parse {config_path}: {exc}")
            return

    dashboard = data.get("dashboard")
    if not isinstance(dashboard, dict):
        dashboard = {}
        data["dashboard"] = dashboard
    dashboard["theme"] = "aiciv-living-record"
    # A user font override would defeat the brand's one-family rule.
    dashboard.pop("font", None)

    print(f"config: set dashboard.theme=aiciv-living-record in {config_path}")
    if dry_run:
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    try:
        config_path.chmod(0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Install AiCIV Living Record dashboard layer")
    parser.add_argument("--hermes-home", type=Path, default=Path.home() / ".hermes")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    theme = repo_root / "brand" / "themes" / "aiciv-living-record.yaml"
    plugin = repo_root / "aiciv" / "plugins" / "aiciv-workspace"

    if not theme.is_file():
        raise SystemExit(f"missing theme: {theme}")
    if not (plugin / "dashboard" / "manifest.json").is_file():
        raise SystemExit(f"missing plugin manifest: {plugin}")

    copy_file(
        theme,
        args.hermes_home / "dashboard-themes" / "aiciv-living-record.yaml",
        dry_run=args.dry_run,
    )
    copy_tree(
        plugin,
        args.hermes_home / "plugins" / "aiciv-workspace",
        dry_run=args.dry_run,
    )
    select_theme(args.hermes_home / "config.yaml", dry_run=args.dry_run)

    print("AiCIV dashboard layer installed. Restart or rescan the Hermes dashboard to load it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
