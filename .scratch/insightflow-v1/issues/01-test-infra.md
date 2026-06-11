# 01 — 测试基础设施

Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to build

搭建 InsightFlow 后端的测试基础设施，使后续所有切片可以 TDD 开发。包括：

- 配置 pytest 及核心插件（pytest-asyncio 用于异步测试）
- 引入 `InsightMemoryRepository` 作为确定性测试用数据层（已在 `src/be/common/insight_memory_repository.py` 中实现）
- 通过 LLMGateway 的 mock 模式替代真实 LLM 调用
- 利用 FastAPI `TestClient` + `app.dependency_overrides` 实现 API 层测试
- 编写一个"健康检查"测试验证基础设施正常（创建 app、调 TestClient 获取 200）

## Acceptance criteria

- [ ] 运行 `pytest tests/` 全部通过（即使只有一个健康检查测试）
- [ ] `InsightMemoryRepository` 可正确初始化并使用
- [ ] `LLMGateway` mock 模式可返回预设响应
- [ ] 测试配置与生产配置隔离（不依赖真实 SQLite 文件/本地状态文件/外部 LLM API）

## Blocked by

None — 可以直接开始
