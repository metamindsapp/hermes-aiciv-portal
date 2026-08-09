import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "dashboard" / "dist"
TEAMS = DIST / "teams.js"
ENTRY = DIST / "entry.js"


class SemanticTeamsContractTests(unittest.TestCase):
    def test_teams_uses_authoritative_profile_and_work_sources(self):
        text = TEAMS.read_text(encoding="utf-8")
        self.assertIn('PROFILE_API = "/api/plugins/kanban/profiles"', text)
        self.assertIn('BOARD_API = "/api/plugins/kanban/board"', text)
        self.assertIn("SDK.fetchJSON(PROFILE_API)", text)
        self.assertIn("SDK.fetchJSON(BOARD_API)", text)

    def test_semantics_are_evidence_backed_not_presence_fiction(self):
        text = TEAMS.read_text(encoding="utf-8")
        for state in ("Needs attention", "Working", "Ready for review", "Ready", "Scheduled", "Waiting", "Available"):
            self.assertIn(state, text)
        self.assertIn("last_heartbeat_at", text)
        self.assertIn("Profile existence alone is never treated as online presence", text)
        self.assertIn("This does not imply the profile is offline", text)
        self.assertNotIn('state: "Online"', text)

    def test_raw_hermes_work_remains_drilldown(self):
        text = TEAMS.read_text(encoding="utf-8")
        self.assertIn("Open raw Hermes work", text)
        self.assertIn('" · task:" + focus.id', text)
        self.assertIn('"profile:" + row.name', text)

    def test_teams_is_scoped_to_aiciv_root(self):
        text = TEAMS.read_text(encoding="utf-8")
        self.assertIn("function isAiCivRootRoute()", text)
        self.assertIn("if (!isAiCivRootRoute()) return null", text)
        self.assertIn('view !== "teams" && view !== "now"', text)
        self.assertIn('REGISTRY.registerSlot("aiciv-semantic-teams", "post-main"', text)
        self.assertIn('REGISTRY.registerSlot("aiciv-semantic-teams", "sidebar"', text)

    def test_entry_loads_teams_after_existing_capabilities(self):
        text = ENTRY.read_text(encoding="utf-8")
        self.assertLess(text.index('loadScript("decisions.js")'), text.index('loadScript("teams.js")'))

    def test_javascript_parses(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        subprocess.run([node, "--check", str(TEAMS)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
