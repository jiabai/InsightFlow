# InsightFlow v1 — PRD

## Problem Statement

知识工作者在浏览网页、阅读文章时，缺乏引导性思考工具——他们被动消费内容，却无法检验自己是否真正理解了文章的核心观点。而当他们需要对某个话题进行深度研究时，又需要手动在多个搜索引擎间来回切换、逐篇阅读、自行提炼——整个过程耗时且难以保证覆盖全面。

现有工具要么只做"稍后阅读"（Pocket），要么只做"AI总结"（ChatGPT 网页摘要），没有一个产品能将**被动阅读 → 主动问答**和**话题研究 → 聚合报告 → 问答**整合为同一条体验链路。

## Solution

InsightFlow 是一个阅读辅助 + 自主研究的整合平台。它接受两种内容来源——当前网页（阅读会话）或研究话题（研究会话）——然后自动完成分块、生成引导性问题、分类标签等工作，最终以问答交互的形式帮助用户深化理解。

核心体验：
1. 用户浏览网页时，点击扩展即可触发阅读会话，在沉浸式阅读界面中查看 AI 生成的引导性问题
2. 用户提出研究话题时，系统自动搜索聚合多源内容生成报告，然后进入相同的问答交互流程
3. 两种会话共享同一条内容处理管线：Content → Chunk → Questions → 问答交互

## User Stories

### 阅读会话
1. 作为读者，当我正在阅读一篇网页文章时，点击浏览器扩展按钮，系统自动提取该页面的主内容并生成 AI 问题，让我可以立即检验理解程度
2. 作为读者，在沉浸式阅读界面中，我能在左侧阅读原文、右侧查看问题列表，两边不会互相遮挡
3. 作为读者，点击某个 AI 生成的问题后，系统以流式打字效果返回基于原文内容的回答，让我获得即时反馈
4. 作为读者，每道问题都带有层级分类标签（如"网络安全 → XSS攻击"），帮助我按兴趣领域快速定位
5. 作为读者，我能看到内容处理的实时进度（Pending → Processing → Completed），在等待时看到骨架屏和进度提示
6. 作为读者，一旦内容处理完成，所有问题立即可交互，无需刷新页面
7. 作为读者，当处理失败时，我能看到清晰的错误提示，而不是无响应的界面
8. 作为读者，我可以将网页内容一键转换为 Markdown 格式并复制到剪贴板，方便日后引用
9. 作为读者，扩展应该支持任何公开网站，不局限于特定域名

### 研究会话
10. 作为研究者，输入一个研究话题后，系统自动规划搜索策略、调用多源搜索引擎、爬取内容并聚合为一份综合报告
11. 作为研究者，聚合报告中的信息来自多个来源，每个源都标注了出处，让我可以回溯验证
12. 作为研究者，聚合报告自动进入相同的处理管线，生成引导性问题，帮助我发现自己没考虑到的角度
13. 作为研究者，与研究报告的问答交互体验和阅读会话完全一致——同样的侧边栏、流式回答、标签分类

### 通用
14. 作为用户，我的所有数据和会话由匿名 `user_id` 隔离，不依赖注册登录即可使用
15. 作为用户，流式 LLM 回答时逐字呈现（打字机效果），让我感受到实时响应
16. 作为用户，问答交互的上下文限定在原文档/报告范围内，不产生幻觉引用
17. 作为用户，我可以随时退出沉浸式阅读模式，恢复原始网页的无修改状态

## Implementation Decisions

### 架构

- **会话模型**：Session 为顶层交互单元，一个 User 可以有多个 Session。Session 分为 Reading Session（浏览器网页触发）和 Research Session（话题触发）。每个 Session 对应一份 Content。
- **内容管线**：Content → MarkdownSplitter（按标题+长度切割，1000-3000 chars）→ Chunks → QuestionGenerator（LLM 生成问题 + TagGenerator 添加层级标签）→ Questions。处理进度通过 Content Status 状态机追踪。
- **Seam 设计**：五大接缝——Content Extraction（前端）、API Routes、LLMGateway、InsightRepository、StorageInterface。API Routes 为最高测试 seam。
- **前端架构**：浏览器扩展采用 WXT + Vue3 + TypeScript，与后端通过 REST API 通信（上传/状态轮询/问题获取/流式问答）。

### 技术决策

- **LLM 统一网关**：LLMGateway 为所有 LLM 调用的唯一入口，封装同步/流式/模拟三种模式。不再允许路由直接实例化 LLM 客户端。
- **依赖注入**：后端使用 FastAPI `Depends` + `app.state` 管理 InsightRepository、本地状态文件、StorageInterface 生命周期。后台服务（KnowledgeProcessingService）通过构造函数注入依赖。无模块级全局单例。
- **数据访问层**：InsightRepository 抽象协议定义 22 个 CRUD 方法，生产用 SQLite 适配器，测试用 InMemory 适配器。
- **匿名身份**：user_id 和 content_id 均通过 SHA-256 哈希生成，无需注册登录系统。
- **Tag 系统**：统一使用"Tag"（废弃 Label），支持一级/二级层级结构，由 LLM 从 Content 自动提炼。

### 数据模型

数据库三张核心表：`file_metadata`、`chunks`、`questions`。通过 `file_id` 关联，chunks 与 questions 之间通过 `chunk_id` 建立一对多关系。Content 处理状态通过本地状态文件追踪（TTL 7 天）。

### API 契约

| 端点 | 方法 | 用途 |
|------|------|------|
| `/upload/{user_id}` | POST | 上传 Content（Markdown） |
| `/file_status/{content_id}` | GET | 查询 Content 处理状态 |
| `/questions/generate/{user_id}/{content_id}` | POST | 触发异步问题生成 |
| `/questions/{content_id}` | GET | 获取已完成的问题列表 |
| `/llm/query` | POST | 同步 LLM 问答 |
| `/llm/query/stream` | POST | 流式 LLM 问答（SSE） |

## Testing Decisions

### 测试策略

- **外部行为**：测试应验证外部可观察行为（API 请求/响应格式、状态码、流式事件顺序），不测试内部实现细节（具体分块算法、提示词内容）。
- **Seam 策略**：优先通过最高 seam（API Routes）测试，使用 FastAPI `TestClient` + `dependency_overrides` 注入 mock Repository 和 mock LLMGateway。

### 被测模块

| 模块 | 测试 seam | 覆盖重点 |
|------|-----------|----------|
| API Routes | seam 2 | 请求验证、状态码、响应格式、流式 SSE 事件 |
| InsightRepository | seam 4 | CRUD 正确性、并发安全、事务回滚 |
| LLMGateway | seam 3 | 提供商路由、流式/同步切换、mock 模式 |
| Content Extraction | seam 1 | 各类 HTML 结构的主内容提取准确率 |
| StorageInterface | seam 5 | 上传/下载/删除正常+异常路径 |

### 测试先例

- `InsightMemoryRepository` 已提供无 I/O、确定性测试能力，是数据层测试的参考实现
- FastAPI `TestClient` + `dependency_overrides` 是 API 层测试的标准模式
- LLMGateway 已内置 mock 模式，可直接用于测试中的 LLM 替代

## Out of Scope

- 用户注册/登录系统（当前维持匿名 `user_id`）
- 多设备会话同步
- 研究会话的实时搜索（当前为批处理模式）
- 用户自定义 Tag
- 答案生成中的多轮对话/追问
- 离线模式
- 移动端
- 数据导出（PDF/HTML）
- 社会化分享

## Further Notes

- 研究会话模块（`deepresearch_agent/`）当前为实验性质，使用免费 API（效果有限），计划后续用 LangChain 等框架重写后正式集成到主产品管线
- `ai_sdk/` 为 Vercel AI SDK 的 Python 实现，是本项目的依赖库而非领域概念
- PRD 应当随着研究会话模块的成熟度提升而迭代，尤其是 Research Session 自动触发管线、多源合并策略等子流程需要在后续细化

---

Status: ready-for-agent
