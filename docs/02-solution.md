# 02 方案与取舍

## 调用流程

CLI 读取问题、历史和资料路径；每一步将问题、历史、已有动作与工具观察结果发送给 `deepseek-flash`。模型输出一个 JSON 动作：`search(query)`、`read(doc_id)`、`ask_clarification` 或 `finish`。程序执行工具并把结果或错误追加到 Trace，再请模型选择下一步。最多 8 步，超限输出 `incomplete`。

Trace 记录每步动作、参数、返回摘要、可公开的简短决策依据和错误。`examples/deepseek/conflict.json` 展示检索 D01/D02 后继续读取两份原文并追问；`clear_answer.json` 展示读取 D03 后直接结束。没有提交模型内部推理。

## 检索与资料

四份合成资料包含 ID、标题、版本日期、原文和结构化 claim。检索先归一化少量同义词，再用中文双字片段重叠数排序。它不依赖额外向量服务，适合小型封闭语料；真实大规模语料需要分词、混合检索和召回评估。

`read` 返回完整原文。只有已读取文档可被引用，引用片段必须在该原文中逐字出现。若已读取资料对同一 claim 给出不同值，`answered` 会被拒绝并将校验错误回传模型，由模型继续选择动作。程序仅设证据边界，不预设正常、冲突、资料外问题的完整动作路径。

## 模型与框架

使用 DeepSeek Chat Completions API，模型 `deepseek-flash`，通过 Python 标准库 `urllib` 接入。请求关闭思考模式并启用 JSON Output，以减少动作 JSON 混入额外文本的风险；未采用 Agent 框架，因此没有框架 Runtime 依赖。选择原生实现是为了在短时间内让动作、观察和校验边界易于审查。配置位于 `.env.example`。`MockModel` 是确定性流程替身，不作为真实决策证据。

## 状态与错误

答案状态为 `answered`、`needs_clarification`、`insufficient_data`、`tool_error`；模型调用或 JSON 解析失败为 `model_error`；步数耗尽为 `incomplete`。工具异常作为观察结果回传模型，允许其重试、换查询或结束；工具调用上限由同一最大步数约束。
