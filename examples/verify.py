"""Verify committed outputs without contacting a model or trusting the summary file."""
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {
    "clear_answer": "answered",
    "conflict": "needs_clarification",
    "outside": "insufficient_data",
    "rewrite": "answered",
    "followup": "answered",
    "tool_failure": "tool_error",
    "source_changed": "answered",
    "step_limit": "incomplete",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(folder):
    base = {d["id"]: d for d in load(ROOT / "data/documents.json")}
    changed = {d["id"]: d for d in load(ROOT / "data/variants/aligned_documents.json")}
    results = {}
    summary = {item["case"]: item for item in load(folder / "summary.json")}
    assert set(summary) == set(EXPECTED), "summary case list is stale"
    for case, expected_status in EXPECTED.items():
        result = load(folder / (case + ".json"))
        assert result["status"] == expected_status, (case, result["status"])
        assert summary[case]["status"] == result["status"] and summary[case]["steps"] == result["steps"], case
        assert result["input"]["question"] and result["input"]["model"] == folder.name, case
        assert result["steps"] <= result["input"]["max_steps"], case
        assert result["answer"] and isinstance(result["gap"], str), case
        if expected_status in {"needs_clarification", "insufficient_data", "tool_error", "incomplete"}:
            assert result["gap"], case
        docs = changed if case == "source_changed" else base
        read_ids = {e["parameters"]["doc_id"] for e in result["trace"]
                    if e["action"] == "read" and "result" in e}
        for citation in result["citations"]:
            doc_id = citation["doc_id"]
            assert doc_id in read_ids, (case, doc_id)
            assert citation["quote"] in docs[doc_id]["text"], (case, doc_id)
        for index, event in enumerate(result["trace"]):
            assert event["step"] == index + 1 and event["reason"], (case, index)
            expected_next = result["trace"][index + 1]["action"] if index + 1 < len(result["trace"]) else (
                "incomplete" if expected_status == "incomplete" else None)
            assert event["next_action"] == expected_next, (case, index)
            if event["action"] in {"search", "read"}:
                assert event["parameters"] and ("result_summary" in event or "error" in event), (case, index)
        results[case] = result
    assert {c["doc_id"] for c in results["conflict"]["citations"]} == {"D01", "D02"}
    assert [e["action"] for e in results["clear_answer"]["trace"]] != [e["action"] for e in results["conflict"]["trace"]]
    assert results["conflict"]["trace"][-1]["action"] == "ask_clarification"
    assert results["source_changed"]["trace"][-1]["action"] == "finish"
    print(folder.name + ": {}/{} outputs verified; citations and next actions match traces".format(
        len(results), len(EXPECTED)))


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
    if model not in {"deepseek", "mock"}:
        raise SystemExit("usage: python3 examples/verify.py [deepseek|mock]")
    verify(ROOT / "examples" / model)
