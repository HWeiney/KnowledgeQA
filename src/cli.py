import argparse
import json
import sys
from pathlib import Path

from .agent import run_agent
from .model import DeepSeekModel, MockModel
from .tools import DocumentTools


def main():
    parser = argparse.ArgumentParser(description="企业知识问答 Agent")
    parser.add_argument("question", help="员工问题")
    parser.add_argument("--model", choices=["deepseek", "mock"], default="deepseek")
    parser.add_argument("--history-file", help="包含历史对话的 JSON 文件")
    parser.add_argument("--trace-file", help="保存实际输出与 Trace 的 JSON 文件")
    parser.add_argument("--data", help="替换文档 JSON 文件")
    parser.add_argument("--fail-tool", choices=["search", "read"], help="故障注入，仅用于评测")
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")
    history = json.loads(Path(args.history_file).read_text(encoding="utf-8")) if args.history_file else []
    model = DeepSeekModel() if args.model == "deepseek" else MockModel()
    tools = DocumentTools(args.data, args.fail_tool) if args.data else DocumentTools(fail_tool=args.fail_tool)
    output = run_agent(args.question, model, tools, history, args.max_steps)
    output["input"] = {"question": args.question, "history": history, "model": args.model,
                       "fail_tool": args.fail_tool, "max_steps": args.max_steps}
    text = json.dumps(output, ensure_ascii=False, indent=2)
    print(text)
    if args.trace_file:
        Path(args.trace_file).write_text(text + "\n", encoding="utf-8")
    return 0 if output["status"] in {"answered", "needs_clarification", "insufficient_data"} else 2


if __name__ == "__main__":
    sys.exit(main())
