import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "dashboard"
ENTRY = DASHBOARD / "dist" / "entry.js"
RUNTIME = DASHBOARD / "dist" / "talk-live.js"
MANIFEST = DASHBOARD / "manifest.json"


class TalkLiveContractTests(unittest.TestCase):
    def test_manifest_uses_modular_entrypoint(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["entry"], "dist/entry.js")
        self.assertGreaterEqual(tuple(map(int, manifest["version"].split("."))), (0, 2, 0))

    def test_entry_loads_existing_workspace_before_voice_runtime(self):
        text = ENTRY.read_text(encoding="utf-8")
        self.assertIn('loadScript("index.js")', text)
        self.assertIn('loadScript("talk-live.js")', text)
        self.assertLess(text.index('loadScript("index.js")'), text.index('loadScript("talk-live.js")'))

    def test_real_webrtc_contract_is_present(self):
        text = RUNTIME.read_text(encoding="utf-8")
        required = [
            "navigator.mediaDevices.getUserMedia",
            'SDK.fetchJSON(endpoint, { method: "POST" })',
            "Conversation.startSession",
            "conversationToken",
            'connectionType: "webrtc"',
            "onStatusChange",
            "onModeChange",
            "setMicMuted",
            "endSession",
            'aiciv:presence:state',
        ]
        for marker in required:
            self.assertIn(marker, text)

    def test_sdk_is_exactly_pinned_and_lazy(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("@elevenlabs/client@1.11.1/dist/lib.iife.js", text)
        self.assertIn("document.createElement(\"script\")", text)
        self.assertIn("ELEVENLABS_CLIENT_VERSION = \"1.11.1\"", text)

    def test_browser_bundle_contains_no_long_lived_secret_names(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ENTRY, RUNTIME, DASHBOARD / "dist" / "index.js")
        )
        for forbidden in (
            "ELEVENLABS_API_KEY",
            "OPENAI_API_KEY",
            "PRESENCE_GATEWAY_API_KEY",
            "AICIV_CALLBACK_API_KEY",
        ):
            self.assertNotIn(forbidden, combined)

    def test_browser_accepts_only_same_plugin_voice_token_endpoint(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('endpoint.startsWith("/api/plugins/aiciv-workspace/")', text)
        self.assertNotIn("participantName", text)
        self.assertNotIn("continuityKey", text)

    def test_javascript_parses_when_node_is_available(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        for path in (ENTRY, RUNTIME, DASHBOARD / "dist" / "index.js"):
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
