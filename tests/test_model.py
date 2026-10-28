import io
import json
import os
import unittest
from unittest.mock import patch

from src.model import DeepSeekModel


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class ModelContractTests(unittest.TestCase):
    def test_structured_decision_disables_thinking(self):
        payload = {"choices": [{"finish_reason": "stop", "message": {"content": '{"action":"search","query":"邮箱"}'}}]}
        sent = {}

        def fake_urlopen(request, timeout):
            sent.update(json.loads(request.data))
            return FakeResponse(json.dumps(payload).encode())

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}), patch("urllib.request.urlopen", fake_urlopen):
            decision = DeepSeekModel().decide([{"role": "user", "content": "json"}])
        self.assertEqual(decision["action"], "search")
        self.assertEqual(sent["thinking"], {"type": "disabled"})
        self.assertEqual(sent["response_format"], {"type": "json_object"})

    def test_trailing_text_is_audited(self):
        payload = {"choices": [{"finish_reason": "stop", "message": {"content":
                   '{"action":"search","query":"食堂"}\nextra model text'}}]}

        def fake_urlopen(request, timeout):
            return FakeResponse(json.dumps(payload).encode())

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}), patch("urllib.request.urlopen", fake_urlopen):
            decision = DeepSeekModel().decide([{"role": "user", "content": "json"}])
        self.assertEqual(decision["action"], "search")
        self.assertIn("trailing text", decision["_format_warning"])


if __name__ == "__main__":
    unittest.main()
