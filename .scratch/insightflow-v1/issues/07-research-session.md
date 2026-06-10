# 07 — 研究会话

Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

流式问答阶段的增强模块。当用户点击问题触发流式回答时，研究会话作为辅助模块被调用，去搜索更多外部资料来丰富和增强 LLM 的回答质量。

- 接收当前 Question 文本和 Content 上下文 → 生成搜索策略 → 调用多源搜索 API → 爬取结果页面 → 聚合为补充资料
- 聚合资料作为额外上下文注入流式 LLM 的 prompt，使回答超出原文档范围但保持有据可查
- 至少支持 2 个搜索提供商，去重后返回相关结果
- 每个引用标注来源 URL，在流式回答中可追溯
- 该模块当前处于实验阶段（`deepresearch_agent/`），后续通过 LangChain 重写，但接口保持稳定

## Acceptance criteria

- [ ] 接收 Question + Context → 生成搜索策略（由 LLM 规划搜索关键词）
- [ ] 搜索至少覆盖 2 个提供商，去重后返回 ≥ 3 条相关结果
- [ ] 每个搜索结果成功爬取主内容，失败时静默跳过
- [ ] 聚合资料以结构化格式注入流式 LLM 的上下文窗口
- [ ] 流式回答中包含来源标注（如 "[来源: example.com]")
- [ ] 研究会话失败时不影响主回答流程（降级为仅基于原文回答）

## Blocked by

- `06-sync-qa` — 需要同步问答的 Question/Context 交互模型
