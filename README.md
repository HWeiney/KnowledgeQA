# 企业知识问答 Agent（题号：企业知识问答）

员工输入制度或产品问题，Agent 通过本地检索与片段读取工具查证，再由 DeepSeek `deepseek-flash` 选择下一步。CLI 输出答案、逐字引用、资料缺口、任务状态和可审计 Trace。

## 评审入口

- [真实模型运行结果](examples/deepseek/summary.json)：六个验收用例及一次资料替换实验；逐案 JSON 包含输入、实际输出和完整 Trace。
- [评估报告](docs/03-evaluation.md)：预期、实测、失败与边界。
- [核心循环](src/agent.py)：模型选动作、工具执行、观察结果回传与步数上限。
- [离线测试](tests/test_agent.py)：不需要 API Key。

## 环境与运行

Python 3.9+，无第三方运行依赖。将 `.env.example` 复制为 `.env`，填入自己的 `DEEPSEEK_API_KEY`。`.env` 已被 Git 忽略，不要提交密钥。默认模型与地址取自 [DeepSeek 官方快速入门](https://api-docs.deepseek.com/quick_start/agent_integrations/)；可用 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL` 覆盖。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.cli '忘记企业邮箱密码怎么办' --model deepseek
python3 -m src.cli '报销期限多久' --model deepseek --trace-file examples/my_run.json
python3 -m src.cli '多久生效？' --model deepseek --history-file examples/history.json
```

没有模型凭据时，可运行 `--model mock`；它只验证工具和流程，不证明真实模型决策效果。

```bash
python3 -m src.cli '报销期限多久' --model mock
python3 examples/generate.py --model mock
python3 examples/generate.py --model deepseek
```

`--fail-tool search` 或 `--fail-tool read` 注入故障；`--max-steps 8` 控制最大模型决策步数；`--data path/to/docs.json` 替换资料。输出状态：`answered`、`needs_clarification`、`insufficient_data`、`tool_error`、`model_error`、`incomplete`。CLI 对 `tool_error`、`model_error`、`incomplete` 返回退出码 2，其余返回 0。

## 目录

- `src/`：Agent 循环、模型接口、检索和读取工具、CLI。
- `data/`：合成制度和 FAQ；`data/variants/` 为资料替换实验。
- `tests/`：可执行单元测试。
- `examples/deepseek/`：真实模型实际输出；`examples/mock/`：离线流程输出。
- `docs/`：需求、方案、评估、AI 使用与复盘。

文档和员工资料均为合成数据，不代表真实企业政策。
