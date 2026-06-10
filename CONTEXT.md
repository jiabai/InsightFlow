# InsightFlow

一个阅读辅助 + 自主研究的整合工具，帮助用户将内容转化为结构化问答以深化理解。

## Language

### 实体

**User**（用户）：
使用该产品的匿名个体。通过前端 SHA-256 哈希自动生成的 `user_id` 标识，用于数据隔离。当前无注册/登录系统。
_Avoid_: 账户（Account）、账号、客户端（Client）

**Session**（会话）：
一次完整的交互过程，涵盖内容获取 → 切片 → 问题生成 → 问答的完整管线。分为阅读会话（Reading Session）和研究会话（Research Session）两种类型。
_Avoid_: 任务（Task）、项目（Project）

**Reading Session**（阅读会话）：
会话类型之一。内容来源为当前浏览器网页，由用户浏览页面时触发。入口为浏览器扩展。
_Avoid_: 阅读模式、浏览会话

**Research Session**（研究会话）：
会话类型之一。内容来源为多源网络搜索聚合，由用户提出研究话题时触发。包含搜索规划、爬取、报告生成等子步骤。当前处于早期阶段（`deepresearch_agent/` 目录）。
_Avoid_: 深度研究、调研任务

**Content**（内容）：
进入处理管线的原材料，一份完整的 Markdown 文档。一个 Session 对应一份 Content。阅读会话的 Content 来自网页提取；研究会话的 Content 来自搜索聚合后生成的综合报告。对应代码中的 File 实体。
_Avoid_: File（文件）、Document（文档）

**Tag**（标签）：
问题的层级分类标记。支持一级/二级层级结构（如"网络安全 → XSS攻击"），由 LLM 从 Content 中自动提炼。对应代码中 `Question.label` 字段和 `tag_management.py` 模块。
_Avoid_: Label、Category（分类）

**Chunk**（切片）：
Content 按 Markdown 标题结构和长度约束（1000-3000 字符）切割后的语义片段。每个 Chunk 是问题生成的最小上下文单元。
_Avoid_: Segment（片段）、Block（块）

**Question**（问题）：
从 Chunk 内容中由 LLM 自动生成的引导性问答条目。每条 Question 包含问题文本、所属 Tag、以及 answered 状态。Questions 是用户与系统交互的核心载体。
_Avoid_: Query（查询）、Prompt（提示词）

## 流程

**Content Status**（内容处理状态）：
Content 在管线中的四阶段状态机：

| 状态 | 含义 |
|------|------|
| **Pending** | 已上传，排队等待处理 |
| **Processing** | 正在分块和生成问题 |
| **Completed** | 问题生成完毕，Session 可交互 |
| **Failed** | 处理出错 |

状态转换方向：Pending → Processing → Completed（成功）或 Failed（失败）。运维上通过 Redis 追踪（TTL 7 天）。
