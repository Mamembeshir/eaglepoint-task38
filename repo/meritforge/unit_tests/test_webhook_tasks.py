import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tasks.webhook_tasks import deliver_webhook


class _FakeDB:
    def __init__(self, scalar_values):
        self.scalar_values = list(scalar_values)
        self.added = []
        self.committed = 0

    def scalar(self, *_args, **_kwargs):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def close(self):
        return None


class _FailingHttpxClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        raise RuntimeError("network down")


class WebhookTasksUnitTests(unittest.TestCase):
    def test_deliver_webhook_moves_to_dead_letter_after_failure(self):
        delivery = SimpleNamespace(
            id="delivery-1",
            webhook_config_id="cfg-1",
            event_name="content.published",
            payload={"id": 1},
            status="queued",
            last_error=None,
            attempts=0,
            response_status=None,
            idempotency_key="idem-1",
            signature=None,
        )
        config = SimpleNamespace(
            id="cfg-1",
            is_active=True,
            url="http://127.0.0.1/webhook",
            headers=None,
            secret=None,
            timeout_seconds=1,
            retry_count=0,
            retry_delay_seconds=1,
            last_failure_at=None,
            failure_count=0,
            last_error=None,
            last_response_status=None,
            success_count=0,
            last_triggered_at=None,
            last_success_at=None,
        )
        fake_db = _FakeDB([delivery, config])

        with patch("app.tasks.webhook_tasks.SessionLocal", return_value=fake_db), \
             patch("app.tasks.webhook_tasks.httpx.Client", _FailingHttpxClient), \
             patch("app.tasks.webhook_tasks.is_intranet_webhook_url", return_value=True):
            result = deliver_webhook("delivery-1")

        self.assertEqual(result["status"], "dead_letter")
        self.assertEqual(delivery.status, "dead_letter")
        self.assertTrue(any(type(obj).__name__ == "WebhookDeadLetter" for obj in fake_db.added))


if __name__ == "__main__":
    unittest.main()
