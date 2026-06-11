# ADR 001: src/extension 架构重构

**日期**: 2026-06-11  
**状态**: Accepted  
**决策者**: grill-with-docs 审查

## 背景

对 `src/extension/` 目录进行领域文档对齐审查后，发现六项关键矛盾需要解决。

## 决策

### 1. 统一 Content 术语（重命名 File → Content）

**决定**: 将代码中所有 `file_id`、`file_status`、`File` 相关命名统一替换为 `content_id`、`content_status`、`Content`。

**理由**: CONTEXT.md 将 Content 定义为核心领域实体，File 只是其存储形式。代码使用 File 造成了领域语言和实现之间的鸿沟。对齐后 CONTEXT.md 成为唯一的术语权威来源。

**影响**:
- `apiService.ts`: `uploadMarkdownContent()` 返回 `UploadResult` 中的 `file_id` → `content_id`
- API 端点: `/upload/{user_id}` 保持不变，但响应体字段重命名
- `statusTracker.cjs`: 状态追踪键名更新
- `ContentScriptAPI.cjs`: 内部方法参数重命名
- 后端需要同步适配（`src/insightflow/` 和 `ai_sdk/` 相关端点）

### 2. 双层层状态机

**决定**: 保留两套状态但建立明确分层。

- **领域层** (API/持久化): `Pending → Processing → Completed/Failed`
- **流水线层** (UI/进度): `idle → extracting → uploading → generating`，作为 Processing 的子状态

**理由**: 领域状态适合外部接口和存储；流水线步骤适合 UI 进度展示。分离后各自职责清晰，避免混淆。

**影响**:
- `statusTracker.cjs` 保持不变但添加与领域状态的映射
- CONTEXT.md 已更新

### 3. Tag 层级标记为 [待实现]

**决定**: 在 CONTEXT.md 中标注 Tag 的一级/二级层级结构为 [待实现]，当前代码中维持扁平字符串。

**理由**: 层级标签是真实设计意图，但代码尚未实现。标注而非删除保留了设计方向，同时诚实地反映当前能力。

### 4. 统一内容提取器

**决定**: 保留 `ContentExtractor.cjs`（新版 class 封装）作为唯一实现，将 `mainContentExtractor.js`（旧版函数式）中的 iframe 处理逻辑迁移过去，然后删除旧版。

**理由**: 两套实现维护成本高。新版 class 封装更符合项目风格且支持更好的测试隔离。iframe 等待逻辑是旧版独有的有价值能力。

**影响**:
- 所有引用 `mainContentExtractor.js` 的代码统一改为 `ContentExtractor.cjs`
- `content.js`、`background.js`、`main.js` 中的 import 需要更新
- 需为新版编写单元测试覆盖 iframe 场景

### 5. API 严格类型化

**决定**: `apiService.ts` 中所有返回 `any` 的方法替换为明确的响应类型接口。

**理由**: `request<T>` 已有泛型基础设施，缺失的只是接口定义。7/13 个 API 方法返回 `any` 意味着超过一半的调用链没有类型保护。

**影响**:
- 新增 `types/api.ts` 定义 `GenerateQuestionsResponse`、`TagListResponse` 等接口
- `apiService.ts` 中所有 `Promise<any>` 替换为具体类型
- 下游 `ContentScriptAPI.cjs` 和 Vue 组件的类型推断自动受益

### 6. MainPage.vue 重组

**决定**: 清理死代码（自引用 import）并将 500+ 行的单体组件拆分为两个 composable。

- `useContentPanel`: 内容面板相关的状态和 API 调用
- `useQuestionList`: 问题列表的状态管理和过滤逻辑

**理由**: 当前组件包含自引用 bug 且职责过多。拆分后组件自身 ~200 行，逻辑可独立测试和复用。

### 7. 目录整理

**决定**: 项目基于 WXT 框架已有合理分层，仅做局部整理：
- 删除重复的 `extractors/` 目录（已合并到 `extractor/`）
- Mobile `sidebar/sidebarQuestion.ts` 保留原位（单文件过度拆分无收益）
- 新增 `hooks/composables/` 存放 MainPage.vue 拆出的 composable

**最终目录**:
```
src/extension/
├── entrypoints/         # WXT 入口点
│   ├── popup/           # 弹窗入口
│   └── services/        # API 服务层
├── components/          # Vue 组件
│   ├── MainPage.vue     # 沉浸式阅读主界面 (~120 行)
│   └── HomePage.vue
├── hooks/               # Vue composables
│   ├── composables/
│   │   ├── useContentPanel.ts    # 内容处理状态管理
│   │   └── useQuestionList.ts    # 问题列表状态管理
│   └── useMarkdownConverter.ts
├── extractor/           # 内容提取器（唯一版本）
│   └── ContentExtractor.cjs
├── immersive/           # 沉浸式阅读引擎
│   ├── apiClient.cjs
│   ├── statusTracker.cjs
│   ├── ... (其余模块)
├── lib/                 # 共享类型和工具
│   ├── apiTypes.ts      # 新增：API 响应类型定义
│   ├── questionTypes.ts
│   └── uploadResult.ts
├── utils/
├── public/
└── wxt.config.ts        # WXT 配置
```

**理由**: WXT 框架的 `entrypoints/` 是其核心约定，强制重组会破坏框架集成。现有结构已满足关注点分离，仅需删除冗余和添加缺失的类型层。

## 后果

- **正面**: 代码结构清晰，领域语言一致，类型安全完整，组件可测试
- **负面**: 一次性改动较大，需要协调前后端同步更新（Content 重命名）
- **风险**: 后端 Content 字段重命名需要部署窗口期，建议前后端分开 PR
