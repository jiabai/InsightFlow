# 05 — 问题生成

Status: ready-for-agent

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

Content 分块处理并自动生成问题的完整链路。上传完成后，沉浸式阅读中自动触发此流程。

- `POST /questions/generate/{user_id}/{content_id}`：触发异步后台任务，由 KnowledgeProcessingService 执行
- `GET /questions/{content_id}`：返回已生成的问题列表（含 Question 文本、所属 Tag、answered 状态）
- MarkdownSplitter 按标题结构和 1000-3000 字符约束切割 Content 为 Chunk
- 每个 Chunk 通过 LLM 生成 3-5 个引导性问题
- TagGenerator 为每个 Question 分配层级标签（一级/二级）
- 问题生成完毕后，在沉浸式阅读右侧侧边栏展示问题列表

## Acceptance criteria

- [ ] Content 被正确切割为多个 Chunk（每个 1000-3000 字，保持标题结构）
- [ ] 每个 Chunk 生成 3-5 个语义完整的问题
- [ ] 每个问题带有层级 Tag（如 "网络安全 → XSS攻击"）
- [ ] 问题生成完成后 Content Status 更新为 Completed
- [ ] 生成过程中 Content Status 为 Processing
- [ ] 生成失败时 Status 更新为 Failed，含错误信息
- [ ] `GET /questions/{content_id}` 在 Completed 状态下返回完整问题列表
- [ ] 问题列表在沉浸式阅读右侧侧边栏中按 Tag 分组展示

## Blocked by

- `04-upload-status` — 需要 Content 可上传、状态可追踪
