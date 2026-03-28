import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.webhook_service import generate_idempotency_key, generate_signature, queue_webhook_event


class _FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, configs, existing_keys=None, duplicate_exists=False):
        self.configs = configs
        self.existing_keys = set(existing_keys or [])
        self.duplicate_exists = duplicate_exists
        self.added = []

    def scalars(self, *_args, **_kwargs):
        return _FakeScalarsResult(self.configs)

    def scalar(self, statement, *_args, **_kwargs):
        if self.duplicate_exists:
            return SimpleNamespace(id="existing")
        statement_str = str(statement)
        if "idempotency_key" not in statement_str:
            return None
        for key in self.existing_keys:
            if key in statement_str:
                return SimpleNamespace(id="existing")
        return None

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None


class WebhookLogicUnitTests(unittest.TestCase):
    def test_generate_signature_is_deterministic(self):
        payload = {"hello": "world", "count": 2}
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()

        sig1 = generate_signature("secret", payload, timestamp)
        sig2 = generate_signature("secret", payload, timestamp)
        sig3 = generate_signature("another-secret", payload, timestamp)

        self.assertEqual(sig1, sig2)
        self.assertNotEqual(sig1, sig3)

    def test_generate_idempotency_key_stable_for_same_payload(self):
        payload_a = {"x": 1, "y": 2}
        payload_b = {"y": 2, "x": 1}

        key1 = generate_idempotency_key("cfg-1", "event.a", payload_a)
        key2 = generate_idempotency_key("cfg-1", "event.a", payload_b)
        key3 = generate_idempotency_key("cfg-2", "event.a", payload_a)

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_queue_webhook_event_skips_duplicate_idempotency_key(self):
        cfg = SimpleNamespace(
            id="cfg-1",
            url="http://internal.local/webhook",
            secret="sec",
            events=["content.published"],
        )
        payload = {"content_id": "abc"}
        existing_key = generate_idempotency_key(str(cfg.id), "content.published", payload)
        db = _FakeDB(configs=[cfg], existing_keys=[existing_key], duplicate_exists=True)

        deliveries = queue_webhook_event(db, "content.published", payload)

        self.assertEqual(deliveries, [])
        self.assertEqual(db.added, [])


if __name__ == "__main__":
    unittest.main()
