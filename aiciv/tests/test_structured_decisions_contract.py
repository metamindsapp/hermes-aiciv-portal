import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "aiciv" / "plugins" / "aiciv-workspace"
DASHBOARD = PLUGIN / "dashboard"
API_PATH = DASHBOARD / "api.py"
DECISIONS_API_PATH = PLUGIN / "decisions_api.py"
DECISIONS_JS = DASHBOARD / "dist" / "decisions.js"
ENTRY = DASHBOARD / "dist" / "entry.js"
MANIFEST = DASHBOARD / "manifest.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class StructuredDecisionsContractTests(unittest.TestCase):
    def test_manifest_uses_composed_api(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["api"], "api.py")
        self.assertEqual(manifest["version"], "0.3.0")

    def test_composed_router_preserves_workspace_and_adds_decisions(self):
        api = load_module(API_PATH, "aiciv_composed_api_test")
        paths = {getattr(route, "path", None) for route in api.router.routes}
        self.assertIn("/presence/ready", paths)
        self.assertIn("/projects", paths)
        self.assertIn("/decisions", paths)
        self.assertIn("/decisions/{decision_id}/respond", paths)

    def test_create_validation_requires_real_options_and_canonical_refs(self):
        api = load_module(DECISIONS_API_PATH, "aiciv_decisions_api_contract")
        valid = api._validate_create(
            {
                "title": "Choose mode",
                "question": "Which rollout mode?",
                "options": [
                    {"id": "safe", "label": "Safe rollout"},
                    {"id": "fast", "label": "Fast rollout"},
                ],
                "recommendation": "safe",
                "evidenceRefs": ["task:t_123"],
                "blockingRefs": ["job:job_123"],
            },
            created_by="test",
        )
        self.assertEqual(valid["recommendation"], "safe")
        self.assertEqual(valid["evidenceRefs"], ["task:t_123"])
        with self.assertRaisesRegex(ValueError, "recommendation_not_an_option"):
            api._validate_create(
                {
                    "title": "Choose mode",
                    "question": "Which rollout mode?",
                    "options": [
                        {"id": "safe", "label": "Safe rollout"},
                        {"id": "fast", "label": "Fast rollout"},
                    ],
                    "recommendation": "invented",
                },
                created_by="test",
            )
        with self.assertRaisesRegex(ValueError, "invalid_evidence_refs"):
            api._validate_create(
                {
                    "title": "Choose mode",
                    "question": "Which rollout mode?",
                    "options": [
                        {"id": "safe", "label": "Safe rollout"},
                        {"id": "fast", "label": "Fast rollout"},
                    ],
                    "evidenceRefs": ["not canonical"],
                },
                created_by="test",
            )

    def test_ui_records_judgment_without_claiming_execution(self):
        text = DECISIONS_JS.read_text(encoding="utf-8")
        self.assertIn('"/respond"', text)
        self.assertIn('method: "POST"', text)
        self.assertIn("Any downstream action still requires its own execution receipt", text)
        self.assertIn("No downstream action is implied by this receipt", text)
        self.assertIn("AiCIV recommendation", text)
        self.assertIn("Evidence", text)
        self.assertIn("Blocking work", text)

    def test_ui_is_scoped_to_aiciv_now_and_needs_you(self):
        text = DECISIONS_JS.read_text(encoding="utf-8")
        self.assertIn("function isAiCivRootRoute()", text)
        self.assertIn("if (!isAiCivRootRoute()) return null", text)
        self.assertIn('view !== "now" && view !== "needs"', text)
        self.assertIn('REGISTRY.registerSlot("aiciv-structured-decisions", "post-main"', text)

    def test_entry_loads_decisions_after_existing_capabilities(self):
        text = ENTRY.read_text(encoding="utf-8")
        self.assertIn('loadStyle("decisions.css")', text)
        core = text.index('loadScript("index.js")')
        voice = text.index('loadScript("talk-live.js")')
        kanban = text.index('loadScript("kanban-projection.js")')
        decisions = text.index('loadScript("decisions.js")')
        self.assertLess(core, voice)
        self.assertLess(voice, kanban)
        self.assertLess(kanban, decisions)

    def test_javascript_parses(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        for path in (DECISIONS_JS, ENTRY):
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
