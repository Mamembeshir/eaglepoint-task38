import unittest

from app.core.audit import REDACTED_VALUE, _redact_sensitive


class AuditRedactionUnitTests(unittest.TestCase):
    def test_redacts_password_token_and_secret_fields(self):
        payload = {
            "email": "user@example.com",
            "password": "plain",
            "refresh_token": "refresh-raw",
            "secret": "webhook-secret",
            "nested": {
                "access_token": "jwt-value",
                "x-webhook-signature": "sig",
            },
        }

        redacted = _redact_sensitive(payload)

        self.assertEqual(redacted["password"], REDACTED_VALUE)
        self.assertEqual(redacted["refresh_token"], REDACTED_VALUE)
        self.assertEqual(redacted["secret"], REDACTED_VALUE)
        self.assertEqual(redacted["nested"]["access_token"], REDACTED_VALUE)
        self.assertEqual(redacted["nested"]["x-webhook-signature"], REDACTED_VALUE)
        self.assertEqual(redacted["email"], "user@example.com")

    def test_redacts_suffix_based_sensitive_keys(self):
        payload = {
            "integration_secret": "abc",
            "session_token": "xyz",
            "safe": "ok",
        }

        redacted = _redact_sensitive(payload)

        self.assertEqual(redacted["integration_secret"], REDACTED_VALUE)
        self.assertEqual(redacted["session_token"], REDACTED_VALUE)
        self.assertEqual(redacted["safe"], "ok")


if __name__ == "__main__":
    unittest.main()
