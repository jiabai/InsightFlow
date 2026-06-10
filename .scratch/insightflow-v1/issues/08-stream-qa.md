# 08 — 流式问答

Status: ready-for-agent

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

在同步问答基础上增加 SSE 流式输出，并在流式过程中调用研究会话来增强回答质量。提供打字机效果的实时回答体验。

- `POST /llm/query/stream`：通过 Server-Sent Events (SSE) 逐字推送 LLM 回答
- 流式生成前，调用研究会话模块搜索补充资料，将搜索结果作为额外上下文注入 LLM
- 前端在沉浸式阅读的问题下方以打字机效果渲染 Markdown 回答，含来源标注
- 流完成后，最终答案持久化并标记 Question 为 answered
- 支持客户端中断流（关闭连接），后端停止生成

## Acceptance criteria

- [ ] SSE 连接正确建立，Content-Type 为 `text/event-stream`
- [ ] 流式生成前调用研究会话，搜索结果注入 LLM context
- [ ] LLM 生成的每个 token 以单独 SSE 事件推送
- [ ] 前端以打字机效果逐字显示，Markdown 格式实时渲染，来源标注可点击
- [ ] 客户端断开连接时后端停止 LLM 生成
- [ ] 流完成后答案完整保存，Question 标记 answered=true
- [ ] 网络中断场景下前端显示重试提示而非崩溃
- [ ] 研究会话失败时降级为仅基于原文的流式回答

## Blocked by

- `07-research-session` — 流式问答调用研究会话来增强回答
