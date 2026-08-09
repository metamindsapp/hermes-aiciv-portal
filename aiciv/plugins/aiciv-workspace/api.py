"""Composed backend router for the AiCIV Hermes dashboard plugin.

Keeps mature workspace/Presence routes isolated from structured Decisions so
new product domains do not grow one monolithic plugin API module.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter


HERE = Path(__file__).resolve().parent
router = APIRouter()


def _load_module(filename: str, module_name: str) -> ModuleType:
    path = HERE / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load AiCIV API module: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_workspace = _load_module("dashboard/plugin_api.py", "aiciv_workspace_api")
_decisions = _load_module("decisions_api.py", "aiciv_decisions_api")

router.include_router(_workspace.router)
router.include_router(_decisions.router)
