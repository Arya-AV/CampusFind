import os
import unittest
from unittest import mock

import app as campus_app


class ConfigTests(unittest.TestCase):
    def test_secret_key_loaded_from_environment(self):
        with mock.patch.dict(os.environ, {"SECRET_KEY": "test-secret-value"}):
            self.assertEqual(campus_app.load_secret_key(), "test-secret-value")

    def test_missing_secret_key_uses_random_fallback(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertLogs(campus_app.app.logger, level="WARNING"):
                first = campus_app.load_secret_key()
                second = campus_app.load_secret_key()
        self.assertTrue(first)
        self.assertNotEqual(first, "change-this-development-key")
        self.assertNotEqual(first, second)

    def test_debug_disabled_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(campus_app.is_debug_enabled())

    def test_debug_enabled_only_by_explicit_setting(self):
        for value in ("1", "true", "TRUE", "yes", "on"):
            with mock.patch.dict(os.environ, {"FLASK_DEBUG": value}, clear=True):
                self.assertTrue(campus_app.is_debug_enabled(), value)
        for value in ("0", "false", "no", ""):
            with mock.patch.dict(os.environ, {"FLASK_DEBUG": value}, clear=True):
                self.assertFalse(campus_app.is_debug_enabled(), value)


if __name__ == "__main__":
    unittest.main()