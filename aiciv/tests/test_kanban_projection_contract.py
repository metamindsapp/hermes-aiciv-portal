import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "dashboard" / "dist"
PROJECTION = DASHBOARD / "kanban-projection.js"
ENTRY = DASHBOARD / "entry.js"


class KanbanProjectionContractTests(unittest.TestCase):
    def test_projection_reads_authoritative_hermes_kanban(self):
        text = PROJECTION.read_text(encoding="utf-8")
        self.assertIn('BOARD_API = "/api/plugins/kanban/board"', text)
        self.assertIn('EVENTS_WS = "/api/plugins/kanban/events"', text)
        self.assertIn("SDK.fetchJSON(BOARD_API)", text)
        self.assertIn("SDK.buildWsUrl(EVENTS_WS", text)
        self.assertIn("latest_event_id", text)

    def test_projection_is_read_only(self):
        text = PROJECTION.read_text(encoding="utf-8")
        for write_marker in ('method: "POST"', 'method: "PUT"', 'method: "PATCH"', 'method: "DELETE"'):
            self.assertNotIn(write_marker, text)

    def test_projection_uses_canonical_task_and_run_references(self):
        text = PROJECTION.read_text(encoding="utf-8")
        self.assertIn('"task:" + task.id', text)
        self.assertIn('"task:" + event.task_id', text)
        self.assertIn('"run:" + event.run_id', text)

    def test_projection_surfaces_meaning_before_raw_status(self):
        text = PROJECTION.read_text(encoding="utf-8")
        for label in ("Working", "Needs attention", "Ready for review", "Scheduled"):
            self.assertIn(label, text)
        self.assertIn("Open authoritative board", text)
        self.assertIn("AiCIV will not invent task state", text)

    def test_projection_targets_only_now_and_activity(self):
        text = PROJECTION.read_text(encoding="utf-8")
        self.assertIn('view !== "now" && view !== "activity"', text)
        self.assertIn('REGISTRY.registerSlot("aiciv-kanban-projection", "post-main"', text)

    def test_entry_loads_kanban_after_core_and_voice(self):
        text = ENTRY.read_text(encoding="utf-8")
        core = text.index('loadScript("index.js")')
        voice = text.index('loadScript("talk-live.js")')
        kanban = text.index('loadScript("kanban-projection.js")')
        self.assertLess(core, voice)
        self.assertLess(voice, kanban)

    def test_javascript_parses(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        for path in (PROJECTION, ENTRY):
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
