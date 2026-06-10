# 04 — 上传与状态追踪

Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

后端内容管线的起点。用户在沉浸式阅读中触发上传动作，将提取的 Markdown 内容发送到后端进行状态追踪。

- `POST /upload/{user_id}`：接收 Markdown 内容，存储到 StorageInterface，写入数据库，初始状态 Pending
- `GET /file_status/{content_id}`：查询 Content 当前处理状态
- Redis 中追踪 Content 状态（Pending → Processing → Completed / Failed），TTL 7 天
- 前端在沉浸式阅读视图中轮询状态并展示进度（从"提取完成"到"问题生成中"到"可以问答"）

## Acceptance criteria

- [ ] 上传 Markdown 内容成功返回 `content_id`（SHA-256）
- [ ] 上传后状态初始为 Pending，可通过 `/file_status` 查询
- [ ] 状态正确流转：Pending → Processing → Completed（或 Failed）
- [ ] 无效请求（缺少 user_id、空内容）返回适当错误码
- [ ] 前端在沉浸式阅读中实时反映状态变化
- [ ] 全部 API 端点的参数校验和错误格式通过测试

## Blocked by

- `03-immersive-reading` — 需要在沉浸式阅读视图中触发上传
