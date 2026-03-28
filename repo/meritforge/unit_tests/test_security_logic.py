import unittest
from unittest.mock import patch

from app.core.config import settings
from app.core.security import (
    LEGACY_TOKEN_HASH_KEY_ID,
    get_password_hash,
    hash_token,
    verify_password,
    verify_token_hash,
)


class SecurityLogicUnitTests(unittest.TestCase):
    def setUp(self):
        self.original_current = settings.password_pepper_current
        self.original_previous = list(settings.password_pepper_previous)
        self.original_keys = dict(settings.refresh_token_hash_keys)
        self.original_active_key = settings.refresh_token_hash_active_key_id

    def tearDown(self):
        settings.password_pepper_current = self.original_current
        settings.password_pepper_previous = self.original_previous
        settings.refresh_token_hash_keys = self.original_keys
        settings.refresh_token_hash_active_key_id = self.original_active_key

    def test_password_pepper_rotation_support(self):
        settings.password_pepper_current = "pepper-v1"
        settings.password_pepper_previous = []

        with patch("app.core.security.pwd_context.hash", return_value="hashed-value") as mock_hash:
            hashed = get_password_hash("VerySecret123")
            self.assertEqual(hashed, "hashed-value")
            mock_hash.assert_called_once_with("VerySecret123pepper-v1")

        settings.password_pepper_current = "pepper-v2"
        settings.password_pepper_previous = ["pepper-v1"]

        with patch("app.core.security.pwd_context.verify") as mock_verify:
            mock_verify.side_effect = [False, True]
            self.assertTrue(verify_password("VerySecret123", hashed))
            self.assertEqual(mock_verify.call_args_list[0].args[0], "VerySecret123pepper-v2")
            self.assertEqual(mock_verify.call_args_list[1].args[0], "VerySecret123pepper-v1")

        with patch("app.core.security.pwd_context.verify", return_value=False):
            self.assertFalse(verify_password("WrongPassword", hashed))

    def test_refresh_token_hmac_hash_and_verify(self):
        settings.refresh_token_hash_keys = {"key-2026-01": "super-secret-key"}
        settings.refresh_token_hash_active_key_id = "key-2026-01"

        key_id, token_hash = hash_token("refresh-token-value")
        self.assertEqual(key_id, "key-2026-01")
        self.assertTrue(verify_token_hash("refresh-token-value", token_hash, key_id))
        self.assertFalse(verify_token_hash("different-token", token_hash, key_id))

    def test_refresh_token_legacy_hash_fallback(self):
        settings.refresh_token_hash_keys = {}
        settings.refresh_token_hash_active_key_id = "unknown-key"

        key_id, token_hash = hash_token("legacy-token")
        self.assertEqual(key_id, LEGACY_TOKEN_HASH_KEY_ID)
        self.assertTrue(verify_token_hash("legacy-token", token_hash, key_id))


if __name__ == "__main__":
    unittest.main()
