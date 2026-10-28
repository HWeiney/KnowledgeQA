import json
import os
import urllib.error
import urllib.request


def load_env(path=".env"):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as file:
        for raw in file:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class DeepSeekModel:
    def __init__(self):
        load_env()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is missing; configure .env or use --model mock")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.name = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

    def decide(self, messages):
        body = json.dumps({"model": self.name, "messages": messages, "temperature": 0,
                           "thinking": {"type": "disabled"}, "max_tokens": 800,
                           "response_format": {"type": "json_object"}, "stream": False}).encode()
        request = urllib.request.Request(
            self.base_url + "/chat/completions", data=body,
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError("model HTTP " + str(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("model connection failed: " + str(exc.reason)) from exc
        choice = payload["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ValueError("model JSON was truncated at max_tokens")
        content = choice["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("model returned invalid JSON: " + repr(content[:240])) from exc


class MockModel:
    """Deterministic flow fixture. It does not measure model decision quality."""
    def decide(self, messages):
        state = json.loads(messages[-1]["content"])
        events = state["events"]
        question = state["question"]
        if not events:
            history = state.get("history", [])
            context = " ".join(str(item.get("content", "")) for item in history[-2:])
            query = context + " " + question if history and len(question) <= 8 else question
            return {"action": "search", "query": query, "reason": "查找相关文档"}
        last = events[-1]
        if last.get("error"):
            return {"action": "finish", "status": "tool_error", "answer": "工具失败，无法核实答案。",
                    "citations": [], "gap": last["error"], "reason": "无法取得可靠资料"}
        reads = [e["result"] for e in events if e["action"] == "read" and "result" in e]
        found = [e["result"] for e in events if e["action"] == "search" and "result" in e]
        if found and not found[-1]:
            return {"action": "finish", "status": "insufficient_data", "answer": "现有资料没有相关答案。",
                    "citations": [], "gap": "缺少相关制度或 FAQ", "reason": "检索无结果"}
        unread = [item["id"] for item in found[-1] if item["id"] not in {d["id"] for d in reads}]
        if unread:
            return {"action": "read", "doc_id": unread[0], "reason": "读取原文核对"}
        if len(reads) >= 2 and reads[0].get("claims", {}).get("expense_deadline_days") != reads[1].get("claims", {}).get("expense_deadline_days") and "报销" in question:
            return {"action": "ask_clarification", "status": "needs_clarification", "answer": "两份制度对报销期限有冲突。请确认适用制度。",
                    "citations": [{"doc_id": d["id"], "quote": d["text"].split("。")[0] + "。"} for d in reads[:2]],
                    "gap": "缺少制度适用范围与优先级", "reason": "原文期限不同"}
        d = reads[0]
        return {"action": "finish", "status": "answered", "answer": d["text"],
                "citations": [{"doc_id": d["id"], "quote": d["text"]}], "gap": "", "reason": "找到原文"}
