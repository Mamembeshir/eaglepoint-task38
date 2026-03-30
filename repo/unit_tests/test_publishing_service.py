import unittest
import uuid
from types import SimpleNamespace

from app.core.enums import ContentStatus, SegmentationType
from app.services.publishing_service import deterministic_user_bucket, is_user_in_canary


class _FakeDB:
    def __init__(self, scalar_values):
        self.scalar_values = list(scalar_values)

    def scalar(self, *_args, **_kwargs):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None


class PublishingServiceUnitTests(unittest.TestCase):
    def test_deterministic_user_bucket_is_stable(self):
        user_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
        first = deterministic_user_bucket(user_id)
        second = deterministic_user_bucket(user_id)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 100)

    def test_is_user_in_canary_random_segment(self):
        content_id = uuid.uuid4()
        user_id = uuid.UUID("00000000-0000-4000-8000-000000000010")
        content = SimpleNamespace(id=content_id, status=ContentStatus.PUBLISHED)
        config = SimpleNamespace(is_enabled=True, is_active=True, segmentation_type=SegmentationType.RANDOM, percentage=50)
        fake_db = _FakeDB([content, config])

        visible, reason = is_user_in_canary(fake_db, content_id, user_id)
        expected_bucket = deterministic_user_bucket(user_id)

        self.assertEqual(visible, expected_bucket < 50)
        self.assertEqual(reason, f"deterministic_bucket_{expected_bucket}")

    def test_is_user_in_canary_cohort_segment(self):
        content_id = uuid.uuid4()
        cohort_id = uuid.uuid4()
        user_id = uuid.uuid4()
        content = SimpleNamespace(id=content_id, status=ContentStatus.PUBLISHED)
        config = SimpleNamespace(
            is_enabled=True,
            is_active=True,
            segmentation_type=SegmentationType.COHORT,
            target_cohort_ids=[str(cohort_id)],
        )
        user = SimpleNamespace(id=user_id, cohorts=[SimpleNamespace(id=cohort_id)])
        fake_db = _FakeDB([content, config, user])

        visible, reason = is_user_in_canary(fake_db, content_id, user_id)

        self.assertTrue(visible)
        self.assertEqual(reason, "cohort_match")


if __name__ == "__main__":
    unittest.main()
