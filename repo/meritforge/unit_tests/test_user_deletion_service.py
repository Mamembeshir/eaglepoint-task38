import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.services.user_deletion_service import process_due_user_hard_deletions


class _FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, users):
        self._users = users
        self.deleted = []

    def scalars(self, *_args, **_kwargs):
        return _FakeScalarsResult(self._users)

    def delete(self, obj):
        self.deleted.append(obj.id)


class UserDeletionServiceUnitTests(unittest.TestCase):
    def test_skips_user_with_legal_hold_and_deletes_due_user(self):
        held_user = SimpleNamespace(
            id=uuid.uuid4(),
            email="held@example.com",
            scheduled_deletion_at=datetime.now(timezone.utc),
            legal_hold=True,
            legal_hold_reason="regulatory",
        )
        deletable_user = SimpleNamespace(
            id=uuid.uuid4(),
            email="due@example.com",
            scheduled_deletion_at=datetime.now(timezone.utc),
            legal_hold=False,
            legal_hold_reason=None,
        )
        db = _FakeDB([held_user, deletable_user])

        with patch("app.services.user_deletion_service.write_audit_log") as audit_log:
            deleted_ids = process_due_user_hard_deletions(db, actor=None, request=None, source="test")

        self.assertEqual(deleted_ids, [deletable_user.id])
        self.assertEqual(db.deleted, [deletable_user.id])
        self.assertEqual(audit_log.call_count, 2)


if __name__ == "__main__":
    unittest.main()
