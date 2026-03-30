import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tasks.audit_tasks import RETENTION_DAYS, cleanup_expired_audit_logs


class _FakeDB:
    def __init__(self, rowcount: int):
        self._rowcount = rowcount
        self.committed = False
        self.closed = False

    def execute(self, *_args, **_kwargs):
        return SimpleNamespace(rowcount=self._rowcount)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class AuditTasksUnitTests(unittest.TestCase):
    def test_cleanup_expired_audit_logs_reports_deleted_count(self):
        fake_db = _FakeDB(rowcount=7)
        with patch("app.tasks.audit_tasks.SessionLocal", return_value=fake_db):
            result = cleanup_expired_audit_logs()

        self.assertEqual(result["deleted_count"], 7)
        self.assertEqual(result["retention_days"], RETENTION_DAYS)
        self.assertIn("cutoff", result)
        self.assertTrue(fake_db.committed)
        self.assertTrue(fake_db.closed)


if __name__ == "__main__":
    unittest.main()
