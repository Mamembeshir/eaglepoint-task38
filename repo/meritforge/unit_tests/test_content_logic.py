import re
import unittest
from types import SimpleNamespace

from app.api.v1.content_submission import _compute_risk_policy, _match_term, _resolve_grade


class ContentLogicUnitTests(unittest.TestCase):
    def test_match_term_keyword_boundary(self):
        text = "Risk words: fraud, anti-fraud, and fraudulent."
        keyword_term = SimpleNamespace(term="fraud", is_regex=False)

        matches = _match_term(text, keyword_term)
        self.assertEqual(matches, 2)

    def test_match_term_regex(self):
        text = "Call me at 123-456-7890 or 222-333-4444"
        regex_term = SimpleNamespace(term=r"\d{3}-\d{3}-\d{4}", is_regex=True)

        matches = _match_term(text, regex_term)
        self.assertEqual(matches, 2)

    def test_match_term_invalid_regex_raises(self):
        text = "anything"
        bad_regex = SimpleNamespace(term=r"(", is_regex=True)

        with self.assertRaises(re.error):
            _match_term(text, bad_regex)

    def test_resolve_grade_with_open_ended_rule(self):
        rules = [
            SimpleNamespace(min_score=0, max_score=9, grade="low"),
            SimpleNamespace(min_score=10, max_score=19, grade="medium"),
            SimpleNamespace(min_score=20, max_score=None, grade="high"),
        ]

        self.assertEqual(_resolve_grade(5, rules).grade, "low")
        self.assertEqual(_resolve_grade(15, rules).grade, "medium")
        self.assertEqual(_resolve_grade(99, rules).grade, "high")
        self.assertIsNone(_resolve_grade(-1, rules))

    def test_risk_policy_sets_high_grade_blocking(self):
        rule = SimpleNamespace(grade="high", blocked_until_final_approval=False, required_distinct_reviewers=1)
        blocked, reviewers = _compute_risk_policy(rule)
        self.assertTrue(blocked)
        self.assertEqual(reviewers, 1)

    def test_risk_policy_enforces_medium_two_reviewers(self):
        rule = SimpleNamespace(grade="medium", blocked_until_final_approval=False, required_distinct_reviewers=1)
        blocked, reviewers = _compute_risk_policy(rule)
        self.assertFalse(blocked)
        self.assertEqual(reviewers, 2)


if __name__ == "__main__":
    unittest.main()
