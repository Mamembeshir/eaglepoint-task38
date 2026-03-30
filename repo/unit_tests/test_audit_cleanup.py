import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.tasks.audit_tasks import RETENTION_DAYS, cleanup_expired_audit_logs


TEST_TAG = uuid.uuid4().hex[:10]


class AuditCleanupTaskTests(unittest.TestCase):
    def test_cleanup_expired_audit_logs_deletes_rows_before_cutoff_only(self):
        db = SessionLocal()
        old_id = str(uuid.uuid4())
        new_id = str(uuid.uuid4())
        try:
            db.execute(
                text(
                    """
                    INSERT INTO audit_logs (
                        id, action, entity_type, entity_id, user_email,
                        description, request_url, request_method, created_at
                    ) VALUES (
                        :id, :action, :entity_type, :entity_id, :user_email,
                        :description, :request_url, :request_method, :created_at
                    )
                    """
                ),
                {
                    "id": old_id,
                    "action": "update",
                    "entity_type": f"cleanup-test-{TEST_TAG}",
                    "entity_id": "old",
                    "user_email": f"old.{TEST_TAG}@example.com",
                    "description": "old audit row",
                    "request_url": "/old",
                    "request_method": "PATCH",
                    "created_at": datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS + 2),
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO audit_logs (
                        id, action, entity_type, entity_id, user_email,
                        description, request_url, request_method, created_at
                    ) VALUES (
                        :id, :action, :entity_type, :entity_id, :user_email,
                        :description, :request_url, :request_method, :created_at
                    )
                    """
                ),
                {
                    "id": new_id,
                    "action": "update",
                    "entity_type": f"cleanup-test-{TEST_TAG}",
                    "entity_id": "new",
                    "user_email": f"new.{TEST_TAG}@example.com",
                    "description": "new audit row",
                    "request_url": "/new",
                    "request_method": "PATCH",
                    "created_at": datetime.now(timezone.utc),
                },
            )
            db.commit()
        finally:
            db.close()

        result = cleanup_expired_audit_logs()
        self.assertGreaterEqual(result["deleted_count"], 1)

        db = SessionLocal()
        try:
            old_row = db.execute(text("SELECT id FROM audit_logs WHERE id = :id"), {"id": old_id}).first()
            new_row = db.execute(text("SELECT id FROM audit_logs WHERE id = :id"), {"id": new_id}).first()
            self.assertIsNone(old_row)
            self.assertIsNotNone(new_row)

            db.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": new_id})
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
