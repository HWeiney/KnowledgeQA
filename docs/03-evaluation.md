# 03 评估：预期、实测与限制

评测日期：2026-10-28。命令：`python3 -m unittest discover -s tests -v`，结果 7/7 通过。真实模型使用 `deepseek-flash`、温度 0；资料为 `data/documents.json`。每个链接含输入、实际输出、状态和逐步 Trace，不能把 Mock 结果当作模型决策证据。

| 验收点 | 预期 | 真实模型实际结果 |
| --- | --- | --- |
| 明确答案 | 读取 FAQ 后回答并引用 | [clear_answer.json](../examples/deepseek/clear_answer.json)：`answered`，`search → read D03 → finish` |
| 文档冲突 | 同时引用 D01/D02，要求确认制度 | [conflict.json](../examples/deepseek/conflict.json)：`needs_clarification`，`search → read D01 → read D02 → ask_clarification` |
| 资料外问题 | 说明缺口 | [outside.json](../examples/deepseek/outside.json)：`insufficient_data`，多次补充检索后结束 |
| 改写问题 | 找到邮箱 FAQ | [rewrite.json](../examples/deepseek/rewrite.json)：`answered`，引用 D03 |
| 上下文追问 | 关联邮箱密码重置并回答生效时间 | [followup.json](../examples/deepseek/followup.json)：`answered`，引用 D03 |
| 工具失败 | 报错并不给无依据答案 | [tool_failure.json](../examples/deepseek/tool_failure.json)：`tool_error`，三次不同查询均收到注入故障后结束 |

两条核心路径的动作由真实模型在看到不同工具结果后生成；它们分别保存在 `clear_answer.json` 和 `conflict.json`。额外的资料替换实验将 D02 的期限及逾期规则改为与 D01 相同，模型从 `ask_clarification` 改为 `finish` 并回答 30 天，见 [source_changed.json](../examples/deepseek/source_changed.json) 和 [替换资料](../data/variants/aligned_documents.json)。这检验了答案与动作对原文变化的响应。

## 失败与限制

- 上下文追问在首次批量运行及一次单独重试时，模型返回非单一 JSON，程序如实给出 `model_error`；再次运行得到上表的成功结果。当前没有格式修复重试，说明该用例仍有模型输出稳定性风险。
- 资料外问题的模型进行了五次检索，能说明缺口但成本偏高；后续可加无结果次数预算。
- 本地双字片段检索只在这套小型合成资料上验证，未测大规模资料、多语言或复杂适用范围。引用校验保证逐字存在，不保证所有自然语言推论都正确。
- `MockModel` 的 [离线结果](../examples/mock/summary.json) 仅用于程序流程和故障注入检查。
- 真实模型运行依赖网络与个人 API Key；评审可用 Mock 完全离线复现工具流程，再自行配置 DeepSeek 复现实验。
