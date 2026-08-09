"""Composed backend router for the AiCIV Hermes dashboard plugin."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter


DASHBOARD_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = DASHBOARD_DIR.parent
router = APIRouter()


def _load(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load AiCIV API module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_workspace = _load(DASHBOARD_DIR / "plugin_api.py", "aiciv_workspace_api")
_decisions = _load(PLUGIN_DIR / "decisions_api.py", "aiciv_decisions_api")

router.include_router(_workspace.router)
router.include_router(_decisions.router)
