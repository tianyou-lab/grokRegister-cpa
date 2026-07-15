import unittest
from unittest.mock import patch

import sso_to_auth_json as s2a


class ExtractNextActionTests(unittest.TestCase):
    def test_extract_create_server_reference(self):
        html = 'createServerReference("401b73e22a5e68737d0037e1aa449fef82cd1b35fb", callServer)'
        ids = s2a._extract_next_action_ids(html)
        self.assertTrue(any(x.startswith("401b73e2") for x in ids))

    def test_fallback_includes_hardcoded(self):
        ids = s2a._extract_next_action_ids("")
        self.assertIn(s2a.NEXT_ACTION_ID.lower(), [x.lower() for x in ids])

    def test_parse_consent_code(self):
        body = (
            '0:{"a":"$@1"}\n'
            '1:{"success":true,"action":"allow","code":"abcXYZ123"}\n'
        )
        self.assertEqual(s2a._parse_consent_code(body), "abcXYZ123")

    def test_sso_to_token_uses_fast_action_without_scanning_chunks(self):
        class FakeCookies:
            def set(self, *args, **kwargs):
                return None

        class FakeResponse:
            def __init__(self, url, text="", status_code=200, payload=None):
                self.url = url
                self.text = text
                self.status_code = status_code
                self._payload = payload or {}

            def json(self):
                return self._payload

        class FakeSession:
            def __init__(self):
                self.cookies = FakeCookies()
                self.proxies = None
                self.posts = []

            def get(self, url, **kwargs):
                if url == "https://accounts.x.ai/":
                    return FakeResponse(url)
                return FakeResponse("https://accounts.x.ai/oauth2/consent?request=1")

            def post(self, url, **kwargs):
                self.posts.append((url, kwargs))
                if "/oauth2/token" in url:
                    return FakeResponse(
                        url,
                        payload={"access_token": "not-a-jwt", "expires_in": 21600},
                    )
                return FakeResponse(
                    url,
                    text='1:{"success":true,"code":"fast-code"}',
                )

        session = FakeSession()
        original_action = s2a._working_next_action_id
        s2a._working_next_action_id = s2a.NEXT_ACTION_ID
        try:
            with patch.object(s2a.requests, "Session", return_value=session), patch.object(
                s2a, "_discover_action_ids_from_js", side_effect=AssertionError("should not scan")
            ):
                token = s2a.sso_to_token("valid-sso", log=lambda message: None)
        finally:
            s2a._working_next_action_id = original_action

        self.assertIsNotNone(token)
        consent_headers = session.posts[0][1]["headers"]
        self.assertEqual(consent_headers["Next-Action"], s2a.NEXT_ACTION_ID)


if __name__ == "__main__":
    unittest.main()
