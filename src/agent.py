import json


SYSTEM = """你是企业知识问答 Agent。每一步只输出一个 JSON 对象，不输出 Markdown 或内部思维过程。
可用动作：
{"action":"search","query":"检索词","reason":"简短依据"}
{"action":"read","doc_id":"D01","reason":"简短依据"}
{"action":"ask_clarification","status":"needs_clarification","answer":"冲突或追问内容","citations":[{"doc_id":"D01","quote":"原文中的连续片段"}],"gap":"还缺什么","reason":"简短依据"}
{"action":"finish","status":"answered|insufficient_data|tool_error","answer":"给用户的答案","citations":[{"doc_id":"D01","quote":"原文中的连续片段"}],"gap":"还缺什么","reason":"简短依据"}
先检索，读取原文后再回答。仅检索摘要不能作为引用。引用必须逐字出自已读取文档。资料不足时继续检索或说明缺口。遇到互相矛盾且无适用范围/优先级依据的资料，列出冲突和两个引用并请求确认，不得擅自选择较新版本。工具失败时可换查询或结束，绝不编造。对话历史可用于理解追问。reason 仅写可公开的简短决策依据。"""


def conflicts(docs):
    by_key = {}
    for d in docs.values():
        for key, value in d.get("claims", {}).items():
            by_key.setdefault(key, {}).setdefault(value, []).append(d["id"])
    return {key: values for key, values in by_key.items() if len(values) > 1}


def validate_final(decision, read_docs):
    status = decision.get("status")
    if status not in {"answered", "insufficient_data", "tool_error", "needs_clarification"}:
        return "invalid status"
    citations = decision.get("citations", [])
    if not isinstance(citations, list):
        return "citations must be a list"
    for c in citations:
        if not isinstance(c, dict) or c.get("doc_id") not in read_docs:
            return "citation refers to an unread document"
        if not c.get("quote") or c["quote"] not in read_docs[c["doc_id"]]["text"]:
            return "citation quote does not match source text"
    if status == "answered" and not citations:
        return "answered requires a source citation"
    if status == "answered" and conflicts(read_docs):
        return "read documents contain unresolved conflicting claims; clarify instead"
    if status == "needs_clarification" and conflicts(read_docs) and len({c["doc_id"] for c in citations}) < 2:
        return "conflict clarification requires both source citations"
    return None


def run_agent(question, model, tools, history=None, max_steps=8):
    events = []
    read_docs = {}
    history = history or []
    for step in range(1, max_steps + 1):
        state = {"question": question, "history": history, "events": events,
                 "remaining_steps": max_steps - step + 1}
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(state, ensure_ascii=False)}]
        try:
            decision = model.decide(messages)
        except Exception as exc:
            return {"status": "model_error", "answer": "模型调用失败，任务未完成。", "citations": [],
                    "gap": str(exc), "trace": events, "steps": step}
        action = decision.get("action")
        event = {"step": step, "action": action, "reason": decision.get("reason", "")}
        if action == "search":
            query = decision.get("query", "")
            event["parameters"] = {"query": query}
            try:
                if not isinstance(query, str) or not query.strip():
                    raise ValueError("search query is empty")
                result = tools.search(query)
                event["result"] = result
                event["result_summary"] = "找到 " + str(len(result)) + " 篇文档：" + ", ".join(d["id"] for d in result)
            except Exception as exc:
                event["error"] = str(exc)
            events.append(event)
        elif action == "read":
            doc_id = decision.get("doc_id", "")
            event["parameters"] = {"doc_id": doc_id}
            try:
                result = tools.read(doc_id)
                read_docs[doc_id] = result
                event["result"] = result
                event["result_summary"] = result["id"] + " 原文：" + result["text"]
            except Exception as exc:
                event["error"] = str(exc)
            events.append(event)
        elif action in {"finish", "ask_clarification"}:
            if action == "ask_clarification":
                decision["status"] = "needs_clarification"
            error = validate_final(decision, read_docs)
            if error:
                event["error"] = error
                events.append(event)
                continue
            event["result_summary"] = "结束：" + decision["status"]
            events.append(event)
            return {"status": decision["status"], "answer": decision.get("answer", ""),
                    "citations": decision.get("citations", []), "gap": decision.get("gap", ""),
                    "trace": events, "steps": step}
        else:
            event["error"] = "invalid action; choose search, read, ask_clarification or finish"
            events.append(event)
    return {"status": "incomplete", "answer": "达到最大执行步数，任务未完成。", "citations": [],
            "gap": "需要继续检索或核实资料", "trace": events, "steps": max_steps}
