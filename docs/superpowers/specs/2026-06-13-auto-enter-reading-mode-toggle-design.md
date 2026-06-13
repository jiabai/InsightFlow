# 自动进入深度阅读模式开关 — 设计文档

- **日期**: 2026-06-13
- **状态**: 已确认（brainstorming 完成，待写实现计划）
- **范围**: `src/extension`（浏览器扩展，WXT + Vue，Manifest V3）

## 1. 目标

给扩展增加一个「是否在页面加载时自动进入深度阅读模式」的**全局开关**。

- 开关**默认关闭**，纯 opt-in，现有用户零感知。
- 开启后，符合门槛的页面在**加载完成时自动进入**全屏深度阅读。
- **手动点击工具栏图标进入的现有行为全程不变**，所有新逻辑只加在「自动」这条路上。

## 2. 背景与约束（代码现状，已核实）

- **入口**: [`entrypoints/background.ts`](../../../src/extension/entrypoints/background.ts) 的 `browser.action.onClicked` →
  `browser.scripting.executeScript({ func: startReadingSession, args: [SITE_RULES] })`，把深度阅读注入当前页。
  目前进入方式 **100% 手动**：没有内容脚本，也没有任何「加载时自动进入」。
- **无 popup（关键约束）**: 构建产物 manifest 的 `action` 只有 `default_icon`、**没有 `default_popup`**。
  原因是 `entrypoints/popup/index.html` 带有 `<meta name="manifest.exclude" content='["chrome","firefox","edge","safari"]'>`，WXT 因此在这些浏览器的构建里排除 popup 入口、不注册 `default_popup` —— 这正是 `onClicked` 能触发的前提。（popup 目录里的 `.vue/.ts` 是未启用的遗留代码。）
  - **硬约束**：
    - 不得移除 `popup/index.html` 里的 `manifest.exclude` meta，也不得给 `action` 添加 `default_popup`。
    - [`wxt.config.ts`](../../../src/extension/wxt.config.ts) 的 `action` 保持只有 `default_icon`。
    - 否则会重新注册 popup，并按 MV3 行为抑制 `onClicked`，打破点击进入。
- **设置存储**: [`lib/storage.ts`](../../../src/extension/lib/storage.ts) 已有 `OptionsState` + `getOptions/saveOptions`（基于 `browser.storage.sync`）。
- **i18n**: `public/_locales/{zh,en,ja,es}/messages.json`，默认 locale `zh`。阅读器内通过 `getI18nMessage(key, fallback)` 取值。
- **可读判定**: [`extractor/siteRules.cjs`](../../../src/extension/extractor/siteRules.cjs) 的 `isReadableUrl` 是**黑名单**——
  仅对显式 `readable:false` 的站点（YouTube、Google 全家桶等约 8 个）返回 `false`，**其余所有 http(s) 页面均返回 `true`**。
  唯一兜底是进入后 `startReadingSession` 内的 `MIN_CONTENT_LENGTH = 500`。
  - **含义**：直接复用现有判定做「全局自动」会几乎接管每个有 500 字正文的页面（含搜索结果页 / 后台 / 应用页），过于激进。
    因此**自动路径必须单独加强门槛**（见 §4.3）。
- **注入上下文**: `startReadingSession` 经 `executeScript({ func })` 注入，运行在 isolated world，
  可用 `chrome.runtime / chrome.i18n / chrome.storage`（代码已用前两者）。它是**自包含函数，不能 `import` 模块**。

## 3. 已确认的决策

1. **触发范围 = 全局自动**：开关开启 → 所有符合门槛的页面加载完成时自动进入；关闭 → 回到点击图标进入。一个全局开关。
2. **开关位置 = 独立选项页（主开关）+ 阅读器内快捷开关**。
3. **自动门槛 = 加强判定（仅自动路径）**：只在「更像正文」时自动进入；手动点击保持现有宽松判定。

## 4. 详细设计

核心改动 = §4.1–§4.5 五处，边界清晰、各司其职。

### 4.1 存储 · `lib/storage.ts`

- `OptionsState` 增加字段 `autoEnterReadingMode: boolean`。
- `defaultOptions` 设 `autoEnterReadingMode: false`。
- 复用现有 `getOptions / saveOptions`。`getOptions` 用默认值兜底（`{ ...defaultOptions, ...result }`），
  老用户自动得到 `false`，**无需迁移**。

### 4.2 触发机制 · `entrypoints/background.ts`

- **抽出共享函数** `injectReadingSession(tabId, url, { mode })`，`mode: 'manual' | 'auto'`，
  封装现有 `executeScript({ func: startReadingSession, args: [SITE_RULES, opts] })`：
  - `manual`：`opts = {}`（宽松，min 500）；失败/抛错时按现状 `notifyFailure(...)`。
  - `auto`：`opts = { requireArticleLike: true, minContentLength: 1500 }`；失败/不达标/抛错时**静默**（仅 `debugLog/debugError`，不弹通知）。
- `action.onClicked` 改为调用 `injectReadingSession(tabId, url, { mode: 'manual' })` —— **逻辑等价，行为不变**。
- 新增 `browser.tabs.onUpdated(tabId, changeInfo, tab)` 监听：
  1. **重置导航标记**：当 `changeInfo.status === 'loading' || typeof changeInfo.url === 'string'` 时，
     标记该 tab「本次导航尚未自动进入」（清除 `enteredThisNav.get(tabId)`）。这覆盖整页刷新与 SPA 路由切换。
  2. 仅在 `changeInfo.status === 'complete'` 时继续。
  3. 先走**廉价同步闸**：`isInjectableUrl(tab.url)` && `isReadableUrl(tab.url, SITE_RULES)`，不过则返回。
  4. 若本次导航已自动进入过（`enteredThisNav.get(tabId) === true`）则返回（防多次 `complete` / SPA 抖动重复注入）。
  5. 读 `getOptions()`，`autoEnterReadingMode` 为 `false` 则返回。
  6. 标记 `enteredThisNav.set(tabId, true)`，调用 `injectReadingSession(tabId, url, { mode: 'auto' })`。
- `browser.tabs.onRemoved` 清理 `enteredThisNav`。
- **去重数据结构**：`Map<number, boolean> enteredThisNav`（每 tab「本次导航是否已自动进入」）。
- **Service Worker 非持久**：Map 在 SW 休眠后丢失，属可接受的 best-effort——
  已加载完成的旧标签不会再收到 `complete`，不会被补触发（用户可手动点击）；新导航会产生全新事件链。

> 行为含义：每次**真实导航**（首次加载 / 刷新 / SPA 改 URL）最多自动进入一次；
> 用户手动关闭阅读器后，因没有新导航而**不会立即被重新弹出**。

### 4.3 加强的自动门槛 · `immersive/readingSession.cjs`

- 函数签名扩展为 `startReadingSession(siteRules, opts = {})`，向后兼容（现有单参调用不受影响）。
  - `const minContentLength = opts.minContentLength ?? 500;`（替换原 `MIN_CONTENT_LENGTH` 常量用法）
  - `const requireArticleLike = opts.requireArticleLike === true;`
- 当 `requireArticleLike`（仅 `auto` 传 `true`）时，在抽取完成后判定「是否更像正文」，不达标则**静默**返回 `{ ok: false, reason: 'not-article-like' }`，**不渲染**：
  - `hasContentRule = Boolean(getWebsiteConfig(url, rules)?.contentElem)`（命中 SITE_RULES 实质内容规则），**或**
  - `hasArticleStructure = Boolean(document.querySelector('article, main, [role="main"]'))`，**或**
  - `matchedContentSelector`：抽取 `method` 为 `'selector'` 或以 `'site-rule'` 开头 —— 即正文命中了提取器维护的正文选择器列表（`.rich_media_content`/`.article-content`/`.post-content`/`.entry-content` 等），覆盖像 news.qq.com 这种无语义标签但正文在已知容器里的页面，
  - **且** `extracted.text.length >= minContentLength`（auto = 1500）。
- `manual` 路径 `requireArticleLike` 为 `false`、`minContentLength` 为 500 —— 维持现状宽松判定。
- 阈值（1500）与结构选择器（`article, main, [role="main"]`）为初始值，dogfooding 后可调（见 §8 可调项）。

### 4.4 选项页（新增） · `entrypoints/options/`

- 新增 WXT options 入口：`index.html` + `main.ts` + `App.vue`（Vue，与项目其余部分一致）。
- WXT 自动生成 `options_ui` —— **与 `action` 无关、不碰 onClicked**，满足 §2 硬约束。
- UI：一个开关「加载页面时自动进入深度阅读模式」+ 简短说明。
  - 挂载时 `getOptions()` 读取并回显当前值。
  - 切换时 `saveOptions({ autoEnterReadingMode })` 写回。
  - 文案走 i18n。
- 入口可达性：右键扩展图标 → 选项；或 chrome://extensions → 详情 → 扩展选项。

### 4.5 阅读器内快捷开关 · `immersive/readingSession.cjs`

- 在顶栏（`#insight-flow-header`，现仅 logo）右侧增加一个小开关「自动进入（全局）」。
- 注入函数运行在 isolated world，可直接用 `chrome.storage.sync`：
  - 渲染后异步 `chrome.storage.sync.get('autoEnterReadingMode')` 回显状态。
  - 切换时 `chrome.storage.sync.set({ autoEnterReadingMode })` 写回（字面量 key `'autoEnterReadingMode'`，与 §4.1 字段一致）。
- 语义 = 全局开关的快捷镜像：被自动弹全屏的当下，一键关掉以后就不再自动。文案需明确「全局」，避免误解为「仅本页」。
- 样式沿用顶栏内联 CSS 风格；i18n 走 `getI18nMessage`。

### 4.6 i18n · `public/_locales/{zh,en,ja,es}/messages.json`

新增 message key（四种语言齐全）：

- 选项页：标题、开关标签、说明文案。
- 阅读器内快捷开关：标签 + tooltip。

## 5. 边界情况

- **默认关闭**：fresh install / 老用户为 `false` → 行为与现在完全一致，直到用户主动开启。
- **非 http(s) / 受限 / 黑名单页**：永不自动进入（复用 `isInjectableUrl` + `isReadableUrl`）。
- **薄页 / 非正文页（自动开启时）**：被 §4.3 门槛静默跳过，**不弹失败通知**（避免在每个非文章页刷屏）。
- **手动关闭后不立刻重开**：`enteredThisNav` 标记在「本次导航」内为 `true`，关闭阅读器不产生新导航 → 不会被重新弹出。
- **刷新 / SPA 改 URL**：会重置标记 → 每次真实导航允许一次自动进入。
- **多次 `complete` / SPA 抖动**：被 `enteredThisNav` 标记拦截，不重复注入。
- **选项页自身**：是 `chrome-extension://` 页，不可注入、不可读 → 永不自动进入。
- **选项页与阅读器开关并发写**：写同一 key，后写覆盖；（可选）`storage.onChanged` 可让两处 UI 实时同步。
- **SW 休眠**：`enteredThisNav` 丢失属可接受 best-effort（见 §4.2）。

## 6. 测试策略

> 仓库当前无可见测试框架；以**手动验证**为主，辅以构建产物检查。

**回归（开关关闭 = 现状）**
1. fresh install → 开关 OFF：点击图标仍能进入（手动路径不回归）；任何页面都不自动进入。
2. 任意页面手动点击进入，宽松判定不变（min 500）。

**自动开启**
3. 选项页打开开关 → 加载已知文章（知乎问题 / medium / 带 `<article>` 的博客）→ 自动全屏进入。
4. 加载搜索结果页 / 后台 / 薄页 → **不**自动进入，且**无**错误通知。
5. 黑名单站点（youtube.com）→ 永不自动进入。

**阅读器内快捷开关**
6. 自动弹出的阅读器里把开关关掉 → 再访问另一篇文章不自动进入；选项页回显为「关」。

**导航行为**
7. 关闭自动弹出的阅读器 → 同页不立即重开；刷新该页 → 再次自动进入（每次导航一次）。

**构建产物**
8. `wxt build` → 检查 `.output/chrome-mv3/manifest.json`：`action` 仍只有 `default_icon`、**无 `default_popup`**；`options_ui` 已出现。

## 7. 改动文件清单

**修改**
- `src/extension/lib/storage.ts` — 加 `autoEnterReadingMode` 字段与默认值。
- `src/extension/entrypoints/background.ts` — 抽 `injectReadingSession`；加 `tabs.onUpdated/onRemoved` 与去重。
- `src/extension/immersive/readingSession.cjs` — `opts` 第二参、加强门槛、顶栏快捷开关。
- `src/extension/public/_locales/{zh,en,ja,es}/messages.json` — 新 i18n key。

**新增**
- `src/extension/entrypoints/options/index.html`
- `src/extension/entrypoints/options/main.ts`
- `src/extension/entrypoints/options/App.vue`

**不改**
- `src/extension/wxt.config.ts`（`action` 保持只有 `default_icon`；确认 WXT 自动注入 `options_ui`）。

## 8. 非目标 / 可选（暂不做）

- **按网站记忆 / 站点白名单**：已选全局自动，不做。
- **重新启用 popup**：禁止（§2 硬约束）。
- **工具栏角标显示开关状态**：可选增强，默认不做。
- **阅读器开关与选项页 `storage.onChanged` 实时同步**：可选打磨，默认读时回显即可。
- **清理 `entrypoints/popup/` 孤立文件**：与本需求无关的重构，不在范围内。

**可调项（实现后可按手感微调）**
- 自动门槛正文阈值（初始 1500 字）。
- 「更像正文」结构选择器（初始 `article, main, [role="main"]` + SITE_RULES `contentElem`）。
