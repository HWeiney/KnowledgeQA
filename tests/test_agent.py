import json
import tempfile
import unittest
from pathlib import Path

from src.agent import run_agent, validate_final
from src.model import MockModel
from src.tools import DATA_PATH, DocumentTools


class BadCitationModel:
    def decide(self, messages):
        events = json.loads(messages[-1]["content"])["events"]
        if not events:
            return {"action": "read", "doc_id": "D03", "reason": "取原文"}
        return {"action": "finish", "status": "answered", "answer": "无法验证的回答",
                "citations": [{"doc_id": "D03", "quote": "原文中不存在"}], "gap": "", "reason": "尝试作答"}


class AgentTests(unittest.TestCase):
    def test_rewrite_retrieval(self):
        self.assertEqual(DocumentTools().search("忘记公司邮件登录口令怎么办")[0]["id"], "D03")

    def test_retrieval_dataset(self):
        cases = json.loads((DATA_PATH.parent / "retrieval_cases.json").read_text(encoding="utf-8"))
        tools = DocumentTools()
        for case in cases:
            with self.subTest(query=case["query"]):
                found = [item["id"] for item in tools.search(case["query"])[:3]]
                expected = case["expected_ids"]
                self.assertTrue(set(expected).issubset(found) if expected else not found)

    def test_conflict_is_clarified_with_two_quotes(self):
        result = run_agent("报销期限多久", MockModel(), DocumentTools())
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual({c["doc_id"] for c in result["citations"]}, {"D01", "D02"})
        self.assertEqual([e["action"] for e in result["trace"]],
                         ["search", "read", "read", "ask_clarification"])

    def test_outside_question_has_gap(self):
        result = run_agent("食堂周末营业吗", MockModel(), DocumentTools())
        self.assertEqual(result["status"], "insufficient_data")
        self.assertTrue(result["gap"])

    def test_tool_failure_is_visible(self):
        result = run_agent("报销期限多久", MockModel(), DocumentTools(fail_tool="search"))
        self.assertEqual(result["status"], "tool_error")
        self.assertIn("error", result["trace"][0])

    def test_invalid_quote_and_step_limit(self):
        result = run_agent("企业邮箱密码怎么重置", BadCitationModel(), DocumentTools(), max_steps=2)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("does not match", result["trace"][1]["error"])

    def test_source_replacement_changes_answer(self):
        docs = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        for doc in docs:
            if doc["id"] == "D02":
                doc["text"] = docs[0]["text"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "documents.json"
            path.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
            result = run_agent("报销期限多久", MockModel(), DocumentTools(path))
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0]["doc_id"], "D01")
        self.assertEqual([e["next_action"] for e in result["trace"]],
                         ["read", "read", "finish", None])

    def test_history_followup(self):
        history = [{"role": "user", "content": "企业邮箱密码忘记了怎么办"},
                   {"role": "assistant", "content": "请在邮箱登录页重置。"}]
        result = run_agent("多久生效？", MockModel(), DocumentTools(), history)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"][0]["doc_id"], "D03")

    def test_tool_failure_cannot_name_unread_policy(self):
        decision = {"status": "tool_error", "answer": "请查阅《虚构的报销管理办法》。", "citations": [], "gap": "工具失败"}
        self.assertIn("unread policy", validate_final(decision, {}))

    def test_malformed_final_fields_are_rejected(self):
        decision = {"status": "answered", "answer": "答案", "citations": [{"doc_id": "D03", "quote": 42}], "gap": ""}
        self.assertIn("quote does not match", validate_final(decision, {"D03": DocumentTools().read("D03")}))


if __name__ == "__main__":
    unittest.main()
