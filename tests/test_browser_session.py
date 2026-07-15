import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import browser_session as bs


class BrowserSessionTests(unittest.TestCase):
    def setUp(self):
        bs.configure(get_proxies=lambda: {}, is_debug=lambda: False, extension_path="")
        bs.set_browser_session(None, None)

    def test_create_options_unique_profile(self):
        opts = bs.create_browser_options(unique_profile=True)
        self.assertIsNotNone(opts)
        profile = getattr(bs._tls, "profile_dir", "")
        self.assertTrue(profile)
        self.assertTrue(os.path.isdir(profile))
        self.assertIn("grok-register-chrome", profile.replace("\\", "/"))
        # set_user_data_path 不能搭配 auto_port；必须有 host:port 形式 address
        self.assertIn(":", str(getattr(opts, "address", "") or ""))

    def test_create_options_applies_configured_proxy(self):
        proxy = "http://127.0.0.1:9999"
        bs.configure(
            get_proxies=lambda: {"http": proxy, "https": proxy},
            is_debug=lambda: False,
            extension_path="",
        )
        opts = bs.create_browser_options(unique_profile=False)
        self.assertEqual(getattr(opts, "proxy", ""), proxy)

    def test_session_proxy_bool(self):
        self.assertFalse(bool(bs.browser))
        self.assertFalse(bool(bs.page))
        fake_b, fake_p = object(), object()
        bs.set_browser_session(fake_b, fake_p)
        self.assertTrue(bool(bs.browser))
        self.assertTrue(bool(bs.page))
        bs.set_browser_session(None, None)
        self.assertFalse(bool(bs.browser))

    def test_start_fail_streak(self):
        before = bs.get_start_fail_streak()
        with patch.object(bs, "Chromium", side_effect=RuntimeError("boom")):
            with self.assertRaises(Exception):
                bs.start_browser(log_callback=None)
        self.assertGreaterEqual(bs.get_start_fail_streak(), before + 1)

    def test_debug_mode_skips_stop(self):
        bs.configure(get_proxies=lambda: {}, is_debug=lambda: True, extension_path="")
        mock_browser = MagicMock()
        bs.set_browser_session(mock_browser, object())
        bs.stop_browser(force=False)
        mock_browser.quit.assert_not_called()
        bs.stop_browser(force=True)
        mock_browser.quit.assert_called()


if __name__ == "__main__":
    unittest.main()
