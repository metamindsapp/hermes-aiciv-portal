from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "dashboard" / "plugin_api.py"
SPEC = importlib.util.spec_from_file_location("aiciv_workspace_plugin_api", MODULE_PATH)
assert SPEC and SPEC.loader
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class WorkspacePluginTests(unittest.TestCase):
    def test_atomic_state_round_trip_and_private_mode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "workspace.json"
            previous = os.environ.get("AICIV_HERMES_STATE_FILE")
            os.environ["AICIV_HERMES_STATE_FILE"] = str(path)
            try:
                state = api._empty_state()
                state["projects"]["prj_0123456789abcdef01234567"] = {"title": "Presence"}
                api._write_state_unlocked(state)
                loaded = api._read_state_unlocked()
                self.assertEqual(loaded["projects"]["prj_0123456789abcdef01234567"]["title"], "Presence")
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            finally:
                if previous is None:
                    os.environ.pop("AICIV_HERMES_STATE_FILE", None)
                else:
                    os.environ["AICIV_HERMES_STATE_FILE"] = previous

    def test_canonical_refs_fail_closed(self):
        self.assertEqual(api._canonical_ref("job", "job_0123"), "job:job_0123")
        with self.assertRaises(ValueError):
            api._canonical_ref("bad kind", "x")
        with self.assertRaises(ValueError):
            api._canonical_ref("job", "has whitespace")

    def test_voice_token_separates_surface_from_relationship_continuity(self):
        captured = {}
        original = api._presence_json
        old_civ = os.environ.get("AICIV_CIV_NAME")
        old_human = os.environ.get("AICIV_HUMAN_NAME")

        async def fake_presence(method, path, *, payload=None, auth=True):
            captured.update({"method": method, "path": path, "payload": payload, "auth": auth})
            return {"token": "short-lived", "conversationId": "conv-1"}

        api._presence_json = fake_presence
        os.environ["AICIV_CIV_NAME"] = "Synth"
        os.environ["AICIV_HUMAN_NAME"] = "Corey"
        try:
            response = asyncio.run(api.voice_token(None))
            self.assertEqual(response.status_code, 200)
            body = json.loads(response.body)
            self.assertEqual(body["conversationId"], "conv-1")
            self.assertEqual(captured["payload"]["participantName"], "Synth:Corey:hermes-web")
            self.assertEqual(captured["payload"]["continuityKey"], "Synth:Corey")
            self.assertEqual(captured["payload"]["surface"], "hermes-web")
        finally:
            api._presence_json = original
            if old_civ is None:
                os.environ.pop("AICIV_CIV_NAME", None)
            else:
                os.environ["AICIV_CIV_NAME"] = old_civ
            if old_human is None:
                os.environ.pop("AICIV_HUMAN_NAME", None)
            else:
                os.environ["AICIV_HUMAN_NAME"] = old_human

    def test_cancel_receipt_does_not_claim_cancelled(self):
        original = api._presence_json

        async def fake_presence(method, path, *, payload=None, auth=True):
            return {"job": {"jobId": "job_0123456789abcdef01234567", "status": "cancel_requested"}}

        api._presence_json = fake_presence
        try:
            response = asyncio.run(api.cancel_job("job_0123456789abcdef01234567"))
            self.assertEqual(response.status_code, 202)
            body = json.loads(response.body)
            self.assertEqual(body["job"]["status"], "cancel_requested")
            self.assertEqual(body["semanticReceipt"], "cancel_requested_not_cancelled")
        finally:
            api._presence_json = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
