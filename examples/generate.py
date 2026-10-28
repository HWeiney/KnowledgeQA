"""Generate actual outputs and traces; choose --model deepseek for assessment evidence."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


CASES = [
    ("clear_answer", "忘记企业邮箱密码怎么办", []),
    ("conflict", "报销期限多久", []),
    ("outside", "食堂周末营业吗", []),
    ("rewrite", "忘记公司邮件登录口令怎么办", []),
    ("followup", "多久生效？", ["--history-file", "examples/history.json"]),
    ("tool_failure", "报销期限多久", ["--fail-tool", "search"]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["deepseek", "mock"], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    folder = root / "examples" / args.model
    folder.mkdir(exist_ok=True)
    summary = []
    for name, question, extra in CASES:
        path = folder / (name + ".json")
        cmd = [sys.executable, "-m", "src.cli", question, "--model", args.model,
               "--trace-file", str(path)] + extra
        completed = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
        if not path.exists():
            print(name + ": no output: " + completed.stderr, file=sys.stderr)
            summary.append({"case": name, "error": completed.stderr.strip()})
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        summary.append({"case": name, "status": result["status"], "steps": result["steps"],
                        "exit_code": completed.returncode, "file": str(path.relative_to(root))})
        print(name + ": " + result["status"] + " (" + str(result["steps"]) + " steps)")
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
