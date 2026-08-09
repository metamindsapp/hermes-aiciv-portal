import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "aiciv" / "plugins" / "aiciv-workspace" / "decision_store.py"


def load_store():
    spec = importlib.util.spec_from_file_location("aiciv_decision_store_test", STORE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class DecisionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("AICIV_DECISIONS_DB")
        os.environ["AICIV_DECISIONS_DB"] = str(Path(self.tmp.name) / "decisions.sqlite3")
        self.store = load_store()
        self.payload = {
            "idempotencyKey": "decision-test-0001",
            "title": "Choose rollout mode",
            "question": "Should the AiCIV promote candidate B?",
            "options": [
                {"id": "approve", "label": "Approve B"},
                {"id": "hold", "label": "Keep evaluating"},
            ],
            "recommendation": "approve",
            "rationale": "Candidate B passed the blind eval.",
            "evidenceRefs": ["task:t_eval"],
            "blockingRefs": ["job:job_rollout"],
            "urgency": "high",
            "createdBy": "test-aiciv",
        }

    def tearDown(self):
        if self.previous_db is None:
            os.environ.pop("AICIV_DECISIONS_DB", None)
        else:
            os.environ["AICIV_DECISIONS_DB"] = self.previous_db
        self.tmp.cleanup()

    def test_create_is_idempotent_and_preserves_structured_fields(self):
        first, created = self.store.create_decision(self.payload)
        second, created_again = self.store.create_decision(self.payload)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["decisionId"], second["decisionId"])
        self.assertEqual(first["status"], "pending")
        self.assertEqual(first["recommendation"], "approve")
        self.assertEqual(first["evidenceRefs"], ["task:t_eval"])
        self.assertEqual(first["blockingRefs"], ["job:job_rollout"])

    def test_same_idempotency_key_with_different_request_fails_closed(self):
        self.store.create_decision(self.payload)
        changed = dict(self.payload)
        changed["question"] = "Different question"
        with self.assertRaisesRegex(ValueError, "idempotency_conflict"):
            self.store.create_decision(changed)

    def test_human_response_has_receipt_but_not_execution_semantics(self):
        decision, _ = self.store.create_decision(self.payload)
        resolved, recorded = self.store.respond_decision(
            decision["decisionId"],
            option_id="approve",
            note="Proceed after the final smoke test.",
            request_id="web:response-00000001",
            actor="human",
        )
        self.assertTrue(recorded)
        self.assertEqual(resolved["status"], "resolved")
        receipt = resolved["response"]
        self.assertTrue(receipt["receiptId"].startswith("drcpt_"))
        self.assertEqual(
            receipt["semantics"],
            "human_decision_recorded_not_downstream_execution",
        )
        self.assertNotIn("executed", receipt)
        self.assertNotIn("succeeded", receipt)

    def test_response_request_is_idempotent(self):
        decision, _ = self.store.create_decision(self.payload)
        first, recorded = self.store.respond_decision(
            decision["decisionId"],
            option_id="hold",
            note="Need one more eval.",
            request_id="web:response-00000002",
        )
        second, recorded_again = self.store.respond_decision(
            decision["decisionId"],
            option_id="hold",
            note="Need one more eval.",
            request_id="web:response-00000002",
        )
        self.assertTrue(recorded)
        self.assertFalse(recorded_again)
        self.assertEqual(first["response"]["receiptId"], second["response"]["receiptId"])

    def test_different_response_after_resolution_is_rejected(self):
        decision, _ = self.store.create_decision(self.payload)
        self.store.respond_decision(
            decision["decisionId"],
            option_id="approve",
            note="",
            request_id="web:response-00000003",
        )
        with self.assertRaisesRegex(ValueError, "decision_not_pending"):
            self.store.respond_decision(
                decision["decisionId"],
                option_id="hold",
                note="",
                request_id="web:response-00000004",
            )

    def test_invalid_option_is_rejected(self):
        decision, _ = self.store.create_decision(self.payload)
        with self.assertRaisesRegex(ValueError, "invalid_option"):
            self.store.respond_decision(
                decision["decisionId"],
                option_id="invented",
                note="",
                request_id="web:response-00000005",
            )

    def test_lifecycle_events_are_durable(self):
        decision, _ = self.store.create_decision(self.payload)
        self.store.respond_decision(
            decision["decisionId"],
            option_id="approve",
            note="",
            request_id="web:response-00000006",
        )
        events = self.store.list_events(limit=20)
        kinds = {event["kind"] for event in events}
        self.assertIn("decision.requested", kinds)
        self.assertIn("decision.resolved", kinds)


if __name__ == "__main__":
    unittest.main()
