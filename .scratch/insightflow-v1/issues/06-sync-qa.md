# 06 — 同步问答

Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

用户在沉浸式阅读中点击问题后，通过 LLM 获取上下文关联的同步回答。

- `POST /llm/query`：接收 Question 文本和 Content 上下文，返回 LLM 生成的回答
- 回答限定在原 Content 范围内，避免幻觉引用
- 答案持久化到数据库，Question 的 `answered` 状态标记为 true
- 前端在问题下方展示回答内容，支持 Markdown 渲染

## Acceptance criteria

- [ ] 传入 Question + Content 上下文 → 返回基于上下文的回答
- [ ] 回答中包含对原文的引用（如引用片段）
- [ ] 已回答的 Question 状态变为 answered=true
- [ ] 对不存在的 content_id 返回 404
- [ ] 空问题文本返回 400 验证错误
- [ ] 答案持久化后再次请求不重复调用 LLM（缓存命中）

## Blocked by

- `05-question-generation` — 需要有 Questions 才能回答
