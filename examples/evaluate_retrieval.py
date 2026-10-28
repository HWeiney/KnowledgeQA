"""Compare the shipped retriever with a no-alias character-bigram baseline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.tools import DocumentTools  # noqa: E402


def raw_grams(text):
    text = "".join(text.lower().split())
    return {text[i:i + 2] for i in range(max(0, len(text) - 1))}


def baseline(query, documents):
    q = raw_grams(query)
    scored = []
    for doc in documents:
        score = len(q & raw_grams(doc["title"] + " " + doc["text"]))
        if score:
            scored.append((score, doc["id"]))
    return [doc_id for _, doc_id in sorted(scored, key=lambda item: (-item[0], item[1]))[:3]]


def pass_case(expected, found):
    return set(expected).issubset(found) if expected else not found


def main():
    cases = json.loads((ROOT / "data/retrieval_cases.json").read_text(encoding="utf-8"))
    tools = DocumentTools()
    rows = []
    for case in cases:
        expected = case["expected_ids"]
        basic = baseline(case["query"], tools.documents)
        improved = [item["id"] for item in tools.search(case["query"])[:3]]
        rows.append({"query": case["query"], "expected_ids": expected,
                     "baseline_top3": basic, "baseline_pass": pass_case(expected, basic),
                     "alias_top3": improved, "alias_pass": pass_case(expected, improved)})
    result = {"total": len(rows), "baseline_passed": sum(row["baseline_pass"] for row in rows),
              "alias_passed": sum(row["alias_pass"] for row in rows), "cases": rows}
    path = ROOT / "examples/retrieval_evaluation.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("baseline: {}/{}; aliases: {}/{}".format(result["baseline_passed"], result["total"],
                                                  result["alias_passed"], result["total"]))
    return result


if __name__ == "__main__":
    main()
