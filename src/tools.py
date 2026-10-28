import json
import re
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.json"
ALIASES = {
    "公司邮件": "企业邮箱", "公司邮箱": "企业邮箱", "邮件": "邮箱",
    "口令": "密码", "登录凭证": "密码", "忘了": "忘记", "找回": "重置",
    "多久": "时间", "期限": "时间", "报账": "报销", "费用申请": "报销申请",
}


def normalize(text):
    text = text.lower()
    for old, new in ALIASES.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", "", text)


def grams(text):
    text = normalize(text)
    return {text[i:i + 2] for i in range(max(0, len(text) - 1))}


def source_claims(document):
    """Derive reviewable claim values from source text, never a stale copied value."""
    claims = dict(document.get("claims", {}))
    if "expense_deadline_days" in claims:
        match = re.search(r"费用发生后\s*(\d+)\s*天内提交报销申请", document["text"])
        if match:
            claims["expense_deadline_days"] = match.group(1)
        else:
            claims.pop("expense_deadline_days")
    return claims


class DocumentTools:
    def __init__(self, path=DATA_PATH, fail_tool=None):
        self.documents = json.loads(Path(path).read_text(encoding="utf-8"))
        self.by_id = {d["id"]: d for d in self.documents}
        self.fail_tool = fail_tool

    def search(self, query):
        if self.fail_tool == "search":
            raise RuntimeError("injected search failure")
        q = grams(query)
        ranked = []
        for d in self.documents:
            haystack = d["title"] + " " + d["text"]
            match = len(q & grams(haystack))
            if match:
                ranked.append((match, d))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [{"id": d["id"], "title": d["title"], "version_date": d["version_date"],
                 "score": score, "preview": d["text"][:45]} for score, d in ranked[:5]]

    def read(self, doc_id):
        if self.fail_tool == "read":
            raise RuntimeError("injected read failure")
        if doc_id not in self.by_id:
            raise KeyError("unknown document ID: " + doc_id)
        document = dict(self.by_id[doc_id])
        document["claims"] = source_claims(document)
        return document
