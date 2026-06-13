# 自动进入深度阅读模式开关 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给扩展加一个全局开关：开启后「更像正文」的页面加载完成时自动进入深度阅读模式；默认关闭，手动点击进入的现有行为完全不变。

**Architecture:** 自动触发走后台 `tabs.onUpdated`，复用一个共享的 `injectReadingSession(tabId, mode)`（与手动点击同一条注入路径）；`mode: 'auto'` 时给 `startReadingSession` 传更严的门槛参数并对失败静默。开关状态存 `storage.sync`，由新增的**选项页**（主开关）和**阅读器顶栏快捷开关**两处读写。判定/守卫的纯逻辑抽到 `lib/autoEnter.ts`。

**Tech Stack:** WXT 0.20、Vue 3、TypeScript 5.6（`vue-tsc --noEmit` 类型检查）、Manifest V3、`browser.*`（wxt/browser）、`chrome.storage.sync`。

**关于验证（重要）：** 本仓库**没有测试框架**（scripts 只有 `dev/build/compile/zip`），spec 已确认以手动验证为主。因此本计划用 **`npm run compile`（类型检查）+ `node --check`（`.cjs` 语法）+ `npm run build`（产物/manifest 检查）+ 末尾的手动测试矩阵** 取代 TDD 循环。每个任务仍小步提交。

**命令约定：** `npm`/`node` 命令均**在 `src/extension/` 目录下执行**；`git` 命令在仓库根目录 `D:\Github\InsightFlow` 执行（路径以 `src/extension/...` 给出）。当前分支应为 `feat/auto-enter-reading-mode`。

---

## File Structure

| 文件 | 责任 | 动作 |
| --- | --- | --- |
| `src/extension/lib/storage.ts` | 持久化设置；新增 `autoEnterReadingMode` 字段 | Modify |
| `src/extension/immersive/readingSession.cjs.d.ts` | `startReadingSession` 类型声明（sidecar） | Modify |
| `src/extension/env.d.ts` | 同上类型声明（ambient `declare module`，必须与 sidecar 同步） | Modify |
| `src/extension/lib/autoEnter.ts` | 自动进入的**纯逻辑**：注入参数常量 + `changeInfo` 判定谓词 | Create |
| `src/extension/public/_locales/{zh,en,ja,es}/messages.json` | i18n 文案 | Modify |
| `src/extension/immersive/readingSession.cjs` | 注入函数：`options` 第二参 + 加强门槛 + 顶栏快捷开关 | Modify |
| `src/extension/entrypoints/background.ts` | 抽 `injectReadingSession` + `tabs.onUpdated/onRemoved` 自动触发 | Modify |
| `src/extension/entrypoints/options/index.html` | 选项页 HTML 锚点（注册 `options_ui`） | Create |
| `src/extension/entrypoints/options/main.ts` | 选项页 Vue 挂载 | Create |
| `src/extension/entrypoints/options/App.vue` | 选项页 UI：主开关 | Create |

**硬约束（勿违反）：** 不要给 `entrypoints/popup/` 创建 `index.html`（会注册 popup 并抑制 `action.onClicked`）；不要给 `wxt.config.ts` 的 `action` 加 `default_popup`。

---

## Task 1: 存储字段 `autoEnterReadingMode`

**Files:**
- Modify: `src/extension/lib/storage.ts`

> 注意：该文件用 **Tab 缩进**，编辑时保持一致。

- [ ] **Step 1: 给 `OptionsState` 增加字段**

把 `OptionsState` 改为（新增最后一行）：

```ts
export type OptionsState = {
	useDeffudle: boolean          // 是否启用Deffudle功能
	useReadability: boolean       // 是否启用可读性优化
	wrapInTripleBackticks: boolean // 是否用三重反引号包裹输出
	showSuccessToast: boolean     // 是否显示操作成功的提示框
	showConfetti: boolean         // 是否显示庆祝效果
	autoEnterReadingMode: boolean // 是否在页面加载时自动进入深度阅读模式
}
```

- [ ] **Step 2: 给 `defaultOptions` 增加默认值 `false`**

```ts
export const defaultOptions: OptionsState = {
	useDeffudle: false,
	useReadability: true,
	wrapInTripleBackticks: false,
	showSuccessToast: false,
	showConfetti: false,
	autoEnterReadingMode: false,
}
```

- [ ] **Step 3: 类型检查**

Run (in `src/extension/`): `npm run compile`
Expected: 无错误（exit 0）。

- [ ] **Step 4: 提交**

```bash
git add src/extension/lib/storage.ts
git commit -m "feat(storage): add autoEnterReadingMode option flag"
```

---

## Task 2: 扩展 `startReadingSession` 类型声明

`ReadingSessionResult` / `startReadingSession` 在**两处**声明，必须同步修改：sidecar `.d.ts` 和 `env.d.ts` 里的 `declare module`。两处保持**完全一致**以免类型分叉。

**Files:**
- Modify: `src/extension/immersive/readingSession.cjs.d.ts`
- Modify: `src/extension/env.d.ts:15-23`

- [ ] **Step 1: 改写 sidecar 声明文件**

把 `src/extension/immersive/readingSession.cjs.d.ts` 全文替换为：

```ts
export type ReadingSessionResult =
  | { ok: true; length: number; method: string }
  | { ok: false; error: string; reason?: string };

export type SiteRuleMap = Record<string, unknown>;

export type StartReadingSessionOptions = {
  requireArticleLike?: boolean;
  minContentLength?: number;
};

export function startReadingSession(
  siteRules?: SiteRuleMap | null,
  options?: StartReadingSessionOptions,
): ReadingSessionResult;
```

- [ ] **Step 2: 同步 `env.d.ts` 里的 `declare module` 块**

把 `src/extension/env.d.ts` 中的整段 `declare module '@/immersive/readingSession.cjs' { ... }` 替换为：

```ts
declare module '@/immersive/readingSession.cjs' {
  export type ReadingSessionResult =
    | { ok: true; length: number; method: string }
    | { ok: false; error: string; reason?: string };

  export type SiteRuleMap = Record<string, unknown>;

  export type StartReadingSessionOptions = {
    requireArticleLike?: boolean;
    minContentLength?: number;
  };

  export function startReadingSession(
    siteRules?: SiteRuleMap | null,
    options?: StartReadingSessionOptions,
  ): ReadingSessionResult;
}
```

- [ ] **Step 3: 类型检查**

Run (in `src/extension/`): `npm run compile`
Expected: 无错误（新参数可选，旧调用向后兼容）。

- [ ] **Step 4: 提交**

```bash
git add src/extension/immersive/readingSession.cjs.d.ts src/extension/env.d.ts
git commit -m "feat(types): add StartReadingSessionOptions and reason field"
```

---

## Task 3: 新增纯逻辑模块 `lib/autoEnter.ts`

**Files:**
- Create: `src/extension/lib/autoEnter.ts`

- [ ] **Step 1: 创建文件**

`src/extension/lib/autoEnter.ts`：

```ts
import type { StartReadingSessionOptions } from '@/immersive/readingSession.cjs'

/**
 * 自动进入深度阅读模式时传给 startReadingSession 的注入参数。
 * 加强门槛：仅在「更像正文」且正文足够长时才自动进入（手动点击不受影响）。
 */
export const AUTO_ENTER_INJECT_OPTS: StartReadingSessionOptions = {
  requireArticleLike: true,
  minContentLength: 1500,
}

/** tabs.onUpdated 回调里 changeInfo 的最小形状（只用到这两个字段）。 */
export type TabChangeInfo = {
  status?: string
  url?: string
}

/**
 * 是否是「新的顶层导航开始」事件：整页开始加载，或 SPA 改了 URL。
 * 命中时应清除该 tab 的「本次导航已自动进入」标记，使下一次真实导航能再次自动进入。
 */
export function isNavigationResetEvent(changeInfo: TabChangeInfo): boolean {
  return changeInfo.status === 'loading' || typeof changeInfo.url === 'string'
}

/** 是否是「页面加载完成」事件：这是可以考虑自动进入的时机。 */
export function isEnterCandidateEvent(changeInfo: TabChangeInfo): boolean {
  return changeInfo.status === 'complete'
}
```

- [ ] **Step 2: 类型检查**

Run (in `src/extension/`): `npm run compile`
Expected: 无错误（依赖 Task 2 的 `StartReadingSessionOptions`）。

- [ ] **Step 3: 提交**

```bash
git add src/extension/lib/autoEnter.ts
git commit -m "feat(reading-session): add pure auto-enter decision helpers"
```

---

## Task 4: i18n 文案（4 个语言文件）

每个 `messages.json` 当前最后一个 key 都是 `questionCopyFailed`。把它的块替换为「它本身 + 5 个新 key」，并保持结尾 `}`。

**Files:**
- Modify: `src/extension/public/_locales/zh/messages.json`
- Modify: `src/extension/public/_locales/en/messages.json`
- Modify: `src/extension/public/_locales/ja/messages.json`
- Modify: `src/extension/public/_locales/es/messages.json`

- [ ] **Step 1: 中文 `zh`**

把 `zh/messages.json` 末尾的

```json
  "questionCopyFailed": {
    "message": "复制失败"
  }
}
```

替换为

```json
  "questionCopyFailed": {
    "message": "复制失败"
  },
  "optionsTitle": {
    "message": "InsightFlow 设置"
  },
  "autoEnterReadingModeLabel": {
    "message": "加载页面时自动进入深度阅读模式"
  },
  "autoEnterReadingModeHint": {
    "message": "开启后，被判定为正文文章的页面会在加载完成时自动进入全屏深度阅读。你随时可以关闭；关闭后仍可点击工具栏图标手动进入。"
  },
  "autoEnterToggleLabel": {
    "message": "自动进入（全局）"
  },
  "autoEnterToggleTooltip": {
    "message": "切换是否在加载页面时自动进入深度阅读（全局设置）"
  }
}
```

- [ ] **Step 2: 英文 `en`**

把 `en/messages.json` 末尾的

```json
  "questionCopyFailed": {
    "message": "Copy failed"
  }
}
```

替换为

```json
  "questionCopyFailed": {
    "message": "Copy failed"
  },
  "optionsTitle": {
    "message": "InsightFlow Settings"
  },
  "autoEnterReadingModeLabel": {
    "message": "Automatically enter deep reading mode on page load"
  },
  "autoEnterReadingModeHint": {
    "message": "When on, pages detected as articles automatically open in full-screen deep reading after they finish loading. You can turn it off anytime; when off, you can still click the toolbar icon to enter manually."
  },
  "autoEnterToggleLabel": {
    "message": "Auto-enter (global)"
  },
  "autoEnterToggleTooltip": {
    "message": "Toggle whether to automatically enter deep reading on page load (global setting)"
  }
}
```

- [ ] **Step 3: 日文 `ja`**

把 `ja/messages.json` 末尾的

```json
  "questionCopyFailed": {
    "message": "コピーに失敗しました"
  }
}
```

替换为

```json
  "questionCopyFailed": {
    "message": "コピーに失敗しました"
  },
  "optionsTitle": {
    "message": "InsightFlow 設定"
  },
  "autoEnterReadingModeLabel": {
    "message": "ページ読み込み時に自動で没入型リーディングに入る"
  },
  "autoEnterReadingModeHint": {
    "message": "オンにすると、記事と判定されたページは読み込み完了後に自動で全画面の没入型リーディングを開きます。いつでもオフにでき、オフのときはツールバーのアイコンをクリックして手動で開けます。"
  },
  "autoEnterToggleLabel": {
    "message": "自動で開く（全体）"
  },
  "autoEnterToggleTooltip": {
    "message": "ページ読み込み時に自動で没入型リーディングに入るかを切り替える（全体設定）"
  }
}
```

- [ ] **Step 4: 西班牙文 `es`**

把 `es/messages.json` 末尾的

```json
  "questionCopyFailed": {
    "message": "Error al copiar"
  }
}
```

替换为

```json
  "questionCopyFailed": {
    "message": "Error al copiar"
  },
  "optionsTitle": {
    "message": "Configuración de InsightFlow"
  },
  "autoEnterReadingModeLabel": {
    "message": "Entrar automáticamente en el modo de lectura profunda al cargar la página"
  },
  "autoEnterReadingModeHint": {
    "message": "Cuando está activado, las páginas detectadas como artículos se abren automáticamente en lectura profunda a pantalla completa al terminar de cargar. Puedes desactivarlo cuando quieras; al estar desactivado, aún puedes hacer clic en el icono de la barra de herramientas para entrar manualmente."
  },
  "autoEnterToggleLabel": {
    "message": "Entrada automática (global)"
  },
  "autoEnterToggleTooltip": {
    "message": "Alternar si se entra automáticamente en lectura profunda al cargar la página (ajuste global)"
  }
}
```

- [ ] **Step 5: 校验 4 个 JSON 合法**

Run (in `src/extension/`):

```bash
node -e "['zh','en','ja','es'].forEach(l=>JSON.parse(require('fs').readFileSync('public/_locales/'+l+'/messages.json','utf8')));console.log('ok')"
```

Expected: 输出 `ok`，无异常。

- [ ] **Step 6: 提交**

```bash
git add src/extension/public/_locales/zh/messages.json src/extension/public/_locales/en/messages.json src/extension/public/_locales/ja/messages.json src/extension/public/_locales/es/messages.json
git commit -m "feat(i18n): add messages for auto-enter toggle and options page"
```

---

## Task 5: 加强的自动门槛（`readingSession.cjs`）

给 `startReadingSession` 加第二参 `options`，并在 `requireArticleLike` 时加判定。该文件用 **2 空格缩进**。

**Files:**
- Modify: `src/extension/immersive/readingSession.cjs`

- [ ] **Step 1: 改函数签名，用 options 派生门槛参数**

把开头

```js
function startReadingSession(siteRules = null) {
  const MIN_CONTENT_LENGTH = 500;
  const GENERATE_PORT_NAME = 'insightflow-generate-questions';
```

替换为

```js
function startReadingSession(siteRules = null, options = {}) {
  const requireArticleLike = Boolean(options && options.requireArticleLike === true);
  const minContentLength =
    options && typeof options.minContentLength === 'number' ? options.minContentLength : 500;
  const GENERATE_PORT_NAME = 'insightflow-generate-questions';
```

- [ ] **Step 2: 在 try 块里用新变量 + 增加 article-like 门槛**

把

```js
  try {
    removeExistingSession();

    const extracted = extractReadableContent(document);
    if (extracted.text.length < MIN_CONTENT_LENGTH) {
      return {
        ok: false,
        error: messages.pageContentTooShort,
      };
    }

    renderReadingSession(extracted);

    return {
      ok: true,
      length: extracted.text.length,
      method: extracted.method,
    };
  } catch (error) {
```

替换为

```js
  try {
    removeExistingSession();

    const extracted = extractReadableContent(document);
    if (extracted.text.length < minContentLength) {
      return {
        ok: false,
        error: messages.pageContentTooShort,
        reason: 'too-short',
      };
    }

    if (requireArticleLike && !isArticleLike()) {
      return {
        ok: false,
        error: 'not-article-like',
        reason: 'not-article-like',
      };
    }

    renderReadingSession(extracted);

    return {
      ok: true,
      length: extracted.text.length,
      method: extracted.method,
    };
  } catch (error) {
```

- [ ] **Step 3: 让 `pageContentTooShort` 文案用新变量**

在 `createMessages()` 里把

```js
      pageContentTooShort: getI18nMessage(
        'pageContentTooShort',
        `Page content is shorter than ${MIN_CONTENT_LENGTH} characters`,
        [String(MIN_CONTENT_LENGTH)],
      ),
```

替换为

```js
      pageContentTooShort: getI18nMessage(
        'pageContentTooShort',
        `Page content is shorter than ${minContentLength} characters`,
        [String(minContentLength)],
      ),
```

- [ ] **Step 4: 新增 `isArticleLike()` 函数**

在 `extractReadableContent` 函数定义的右花括号 `}` 之后（即 `function extractBySiteRule(doc, siteRule) {` 之前）插入：

```js
  function isArticleLike() {
    const pageUrl = document.baseURI || document.URL || readingWindow.location?.href || '';
    const siteRule = getWebsiteConfig(pageUrl, activeSiteRules);
    const hasContentRule = Boolean(siteRule && siteRule.contentElem);
    const hasArticleStructure = Boolean(document.querySelector('article, main, [role="main"]'));
    return hasContentRule || hasArticleStructure;
  }

```

- [ ] **Step 5: 语法检查**

Run (in `src/extension/`): `node --check immersive/readingSession.cjs`
Expected: 无输出（语法正确）。

- [ ] **Step 6: 提交**

```bash
git add src/extension/immersive/readingSession.cjs
git commit -m "feat(reading-session): gate auto-enter behind article-like check"
```

---

## Task 6: 后台自动触发（`background.ts`）

抽出共享 `injectReadingSession`，新增 `tabs.onUpdated/onRemoved` 自动触发。该文件用 **2 空格缩进**。

**Files:**
- Modify: `src/extension/entrypoints/background.ts`

- [ ] **Step 1: 增加 import**

把顶部

```ts
import { generateQuestion } from '@/entrypoints/services/apiService';
import { SITE_RULES, isReadableUrl } from '@/extractor/siteRules.cjs';
import { startReadingSession, type ReadingSessionResult } from '@/immersive/readingSession.cjs';
import type { QuestionItem } from '@/lib/questionTypes';
import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';
```

替换为

```ts
import { generateQuestion } from '@/entrypoints/services/apiService';
import { SITE_RULES, isReadableUrl } from '@/extractor/siteRules.cjs';
import { startReadingSession, type ReadingSessionResult } from '@/immersive/readingSession.cjs';
import {
  AUTO_ENTER_INJECT_OPTS,
  isEnterCandidateEvent,
  isNavigationResetEvent,
} from '@/lib/autoEnter';
import { getOptions } from '@/lib/storage';
import type { QuestionItem } from '@/lib/questionTypes';
import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';
```

- [ ] **Step 2: 精简 `onClicked`，调用共享函数 + 注册自动触发**

把

```ts
export default defineBackground(() => {
  debugLog('startup', { portName: GENERATE_PORT_NAME });

  browser.action.onClicked.addListener(async (tab) => {
    const tabId = tab.id;
    debugLog('action:clicked', {
      tabId,
      urlOrigin: getUrlOrigin(tab.url),
      urlSupported: isInjectableUrl(tab.url),
    });

    if (typeof tabId !== 'number' || !isInjectableUrl(tab.url)) {
      await notifyFailure(getMessage('unsupportedPage', 'Current page does not support Reading Sessions'));
      return;
    }

    if (!isReadableUrl(tab.url || '', SITE_RULES)) {
      await notifyFailure(getMessage('unreadableSite', 'This site is not supported for Reading Sessions'));
      return;
    }

    try {
      const [injection] = await browser.scripting.executeScript({
        target: { tabId },
        func: startReadingSession,
        args: [SITE_RULES],
      });
      const result = injection?.result as ReadingSessionResult | undefined;

      if (!result?.ok) {
        throw new Error(result?.error || getMessage('extractContentFailed', 'Could not extract readable content'));
      }

      debugLog('reading-session:injected', {
        tabId,
        contentLength: result.length,
        method: result.method,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      debugError('reading-session:inject-error', error, { tabId });
      await notifyFailure(`${getMessage('enterReadingSessionFailed', 'Unable to enter Reading Session')}: ${message}`);
    }
  });

  setupGenerateQuestionsPort();
  setupLegacyGenerateQuestionsMessage();
});
```

替换为

```ts
export default defineBackground(() => {
  debugLog('startup', { portName: GENERATE_PORT_NAME });

  browser.action.onClicked.addListener(async (tab) => {
    const tabId = tab.id;
    debugLog('action:clicked', {
      tabId,
      urlOrigin: getUrlOrigin(tab.url),
      urlSupported: isInjectableUrl(tab.url),
    });

    if (typeof tabId !== 'number' || !isInjectableUrl(tab.url)) {
      await notifyFailure(getMessage('unsupportedPage', 'Current page does not support Reading Sessions'));
      return;
    }

    if (!isReadableUrl(tab.url || '', SITE_RULES)) {
      await notifyFailure(getMessage('unreadableSite', 'This site is not supported for Reading Sessions'));
      return;
    }

    await injectReadingSession(tabId, 'manual');
  });

  setupAutoEnterReadingMode();
  setupGenerateQuestionsPort();
  setupLegacyGenerateQuestionsMessage();
});

type InjectReadingSessionMode = 'manual' | 'auto';

async function injectReadingSession(tabId: number, mode: InjectReadingSessionMode): Promise<void> {
  const options = mode === 'auto' ? AUTO_ENTER_INJECT_OPTS : {};

  try {
    const [injection] = await browser.scripting.executeScript({
      target: { tabId },
      func: startReadingSession,
      args: [SITE_RULES, options],
    });
    const result = injection?.result as ReadingSessionResult | undefined;

    if (!result?.ok) {
      if (mode === 'manual') {
        throw new Error(result?.error || getMessage('extractContentFailed', 'Could not extract readable content'));
      }
      debugLog('reading-session:auto-skip', { tabId, reason: result?.reason ?? result?.error });
      return;
    }

    debugLog('reading-session:injected', {
      tabId,
      mode,
      contentLength: result.length,
      method: result.method,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    debugError('reading-session:inject-error', error, { tabId, mode });
    if (mode === 'manual') {
      await notifyFailure(`${getMessage('enterReadingSessionFailed', 'Unable to enter Reading Session')}: ${message}`);
    }
  }
}

function setupAutoEnterReadingMode(): void {
  const enteredThisNav = new Map<number, boolean>();

  browser.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // 新导航开始（整页加载或 SPA 改 URL）→ 允许本次导航再自动进入一次。
    if (isNavigationResetEvent(changeInfo)) {
      enteredThisNav.delete(tabId);
    }

    if (!isEnterCandidateEvent(changeInfo)) return;
    if (enteredThisNav.get(tabId)) return;

    const url = tab.url;
    if (!isInjectableUrl(url) || !isReadableUrl(url || '', SITE_RULES)) return;

    const { autoEnterReadingMode } = await getOptions();
    if (!autoEnterReadingMode) return;

    // await 之后再核对一次，防止同一次加载的多个 complete 事件重复注入。
    if (enteredThisNav.get(tabId)) return;
    enteredThisNav.set(tabId, true);

    await injectReadingSession(tabId, 'auto');
  });

  browser.tabs.onRemoved.addListener((tabId) => {
    enteredThisNav.delete(tabId);
  });
}
```

- [ ] **Step 3: 类型检查**

Run (in `src/extension/`): `npm run compile`
Expected: 无错误。

- [ ] **Step 4: 提交**

```bash
git add src/extension/entrypoints/background.ts
git commit -m "feat(background): auto-enter reading mode on page load when enabled"
```

---

## Task 7: 阅读器顶栏快捷开关（`readingSession.cjs`）

在沉浸式阅读顶栏右侧加一个「自动进入（全局）」开关，直接读写 `chrome.storage.sync`。该文件用 **2 空格缩进**。

**Files:**
- Modify: `src/extension/immersive/readingSession.cjs`

- [ ] **Step 1: 在 `createMessages()` 增加两条文案**

把

```js
      exitReadingMode: getI18nMessage('exitReadingModeTooltip', 'Exit Reading Mode'),
```

替换为

```js
      exitReadingMode: getI18nMessage('exitReadingModeTooltip', 'Exit Reading Mode'),
      autoEnterToggle: getI18nMessage('autoEnterToggleLabel', 'Auto-enter (global)'),
      autoEnterToggleTooltip: getI18nMessage(
        'autoEnterToggleTooltip',
        'Toggle auto-entering deep reading on page load (global)',
      ),
```

- [ ] **Step 2: 在顶栏挂上开关**

把

```js
    const wordmark = document.createElement('span');
    wordmark.className = 'insight-flow-wordmark';
    wordmark.textContent = 'InsightFlow';

    header.append(mark, wordmark);
```

替换为

```js
    const wordmark = document.createElement('span');
    wordmark.className = 'insight-flow-wordmark';
    wordmark.textContent = 'InsightFlow';

    const autoToggle = createAutoEnterToggle();

    header.append(mark, wordmark, autoToggle);
```

- [ ] **Step 3: 增加开关 + storage 辅助函数**

在 `createActionIcon()` 函数定义之后插入：

```js
  function createAutoEnterToggle() {
    const label = document.createElement('label');
    label.id = 'insight-flow-auto-toggle';
    label.title = messages.autoEnterToggleTooltip;

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.id = 'insight-flow-auto-toggle-input';

    const text = document.createElement('span');
    text.className = 'insight-flow-auto-toggle-text';
    text.textContent = messages.autoEnterToggle;

    label.append(input, text);

    getStoredAutoEnter().then((enabled) => {
      input.checked = enabled;
    });

    input.addEventListener('change', () => {
      setStoredAutoEnter(input.checked);
    });

    return label;
  }

  function getStoredAutoEnter() {
    return new Promise((resolve) => {
      try {
        const storage = getSyncStorage();
        if (!storage) {
          resolve(false);
          return;
        }
        const maybePromise = storage.get('autoEnterReadingMode', (items) => {
          resolve(Boolean(items && items.autoEnterReadingMode));
        });
        if (maybePromise && typeof maybePromise.then === 'function') {
          maybePromise
            .then((items) => resolve(Boolean(items && items.autoEnterReadingMode)))
            .catch(() => resolve(false));
        }
      } catch {
        resolve(false);
      }
    });
  }

  function setStoredAutoEnter(value) {
    try {
      const storage = getSyncStorage();
      if (!storage) return;
      storage.set({ autoEnterReadingMode: Boolean(value) });
    } catch {
      // Storage 不可用时静默；全局开关仍可从选项页设置。
    }
  }

  function getSyncStorage() {
    const chromeApi =
      (window.chrome && window.chrome) || (globalThis.chrome && globalThis.chrome) || null;
    if (chromeApi && chromeApi.storage && chromeApi.storage.sync) {
      return chromeApi.storage.sync;
    }
    return null;
  }

```

- [ ] **Step 4: 增加开关样式**

在 `renderReadingSession` 内 `style.textContent` 模板里，把

```css
      #insight-flow-header .insight-flow-wordmark {
        color: #f2f2f2 !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0 !important;
      }
```

替换为

```css
      #insight-flow-header .insight-flow-wordmark {
        color: #f2f2f2 !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0 !important;
      }
      #insight-flow-header #insight-flow-auto-toggle {
        margin-left: auto !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        color: #d6d6d6 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        user-select: none !important;
      }
      #insight-flow-header #insight-flow-auto-toggle input {
        width: 16px !important;
        height: 16px !important;
        margin: 0 !important;
        cursor: pointer !important;
        accent-color: #43bf4f !important;
      }
```

- [ ] **Step 5: 语法检查**

Run (in `src/extension/`): `node --check immersive/readingSession.cjs`
Expected: 无输出（语法正确）。

- [ ] **Step 6: 提交**

```bash
git add src/extension/immersive/readingSession.cjs
git commit -m "feat(reading-session): add in-reader auto-enter quick toggle"
```

---

## Task 8: 选项页（主开关）

新建 WXT options 入口（`index.html` + `main.ts` + `App.vue`）。新文件用 **2 空格缩进**。

**Files:**
- Create: `src/extension/entrypoints/options/index.html`
- Create: `src/extension/entrypoints/options/main.ts`
- Create: `src/extension/entrypoints/options/App.vue`

- [ ] **Step 1: `index.html`**

```html
<!doctype html>
<html lang="zh">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>InsightFlow</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="./main.ts"></script>
  </body>
</html>
```

- [ ] **Step 2: `main.ts`**

```ts
import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
```

- [ ] **Step 3: `App.vue`**

```vue
<template>
  <main class="if-options">
    <h1 class="if-options__title">{{ title }}</h1>

    <label class="if-options__row">
      <input type="checkbox" :checked="autoEnter" @change="onToggle" />
      <span class="if-options__label">{{ label }}</span>
    </label>

    <p class="if-options__hint">{{ hint }}</p>
  </main>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { browser } from 'wxt/browser';
import { getOptions, saveOptions } from '@/lib/storage';

const autoEnter = ref(false);

function t(key: string, fallback: string): string {
  try {
    return browser.i18n?.getMessage?.(key) || fallback;
  } catch {
    return fallback;
  }
}

const title = t('optionsTitle', 'InsightFlow Settings');
const label = t('autoEnterReadingModeLabel', 'Automatically enter deep reading mode on page load');
const hint = t(
  'autoEnterReadingModeHint',
  'When on, article pages automatically open in full-screen deep reading after they load.',
);

onMounted(async () => {
  const options = await getOptions();
  autoEnter.value = options.autoEnterReadingMode;
});

async function onToggle(event: Event): Promise<void> {
  const checked = (event.target as HTMLInputElement).checked;
  autoEnter.value = checked;
  await saveOptions({ autoEnterReadingMode: checked });
}
</script>

<style scoped>
.if-options {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 24px;
  font-family: system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;
  color: #1f1f1f;
}
.if-options__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 700;
}
.if-options__row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.if-options__row input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #43bf4f;
}
.if-options__label {
  font-size: 15px;
  font-weight: 600;
}
.if-options__hint {
  margin: 12px 0 0 28px;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}
</style>
```

- [ ] **Step 4: 类型检查 + 构建**

Run (in `src/extension/`): `npm run compile`
Expected: 无错误。

Run (in `src/extension/`): `npm run build`
Expected: 构建成功。

- [ ] **Step 5: 提交**

```bash
git add src/extension/entrypoints/options/index.html src/extension/entrypoints/options/main.ts src/extension/entrypoints/options/App.vue
git commit -m "feat(options): add options page with auto-enter switch"
```

---

## Task 9: 构建产物校验 + 手动测试矩阵

无代码改动；这是验收门。若任一项失败，回到对应任务修复并提交。

**Files:** 无（仅验证）

- [ ] **Step 1: 类型检查与构建**

Run (in `src/extension/`): `npm run compile` → 无错误
Run (in `src/extension/`): `npm run build` → 成功

- [ ] **Step 2: 校验 manifest（关键约束）**

Run (in `src/extension/`):

```bash
node -e "const m=require('./.output/chrome-mv3/manifest.json');console.log(JSON.stringify({action:m.action,options_ui:m.options_ui,hasPopup:!!(m.action&&m.action.default_popup)}))"
```

Expected:
- `hasPopup` 为 `false`（`action` 里**没有** `default_popup`）。
- `action` 只含 `default_icon`。
- `options_ui` 存在（指向 options 页）。

- [ ] **Step 3: 手动测试（在 Chrome 加载 `src/extension/.output/chrome-mv3` 未打包扩展）**

逐项确认：

1. **回归（默认关闭）**：全新加载扩展 → 任意页面**不会**自动进入；点击工具栏图标仍能进入深度阅读（手动路径不回归）。
2. **打开开关**：右键扩展图标 → 选项（或 chrome://extensions → 详情 → 扩展选项）→ 打开开关。
3. **正文页自动进入**：访问一篇文章（知乎问题 / medium / 带 `<article>` 的博客）→ 加载完成后**自动**全屏进入。
4. **非正文页不打扰**：访问搜索结果页 / 后台 / 短页面 → **不**自动进入，且**无**失败通知弹出。
5. **黑名单**：访问 youtube.com → **永不**自动进入。
6. **阅读器内快捷开关**：在自动弹出的阅读器顶栏把「自动进入（全局）」关掉 → 再访问另一篇文章**不**自动进入；回到选项页确认开关已变为关。
7. **导航行为**：关闭自动弹出的阅读器（× 或 Esc）→ 同一页面**不**立即重开；刷新该页 → **再次**自动进入（每次真实导航一次）。
8. **手动始终可用**：无论开关状态，点击工具栏图标都能用宽松判定进入（含未达自动门槛的页面）。

- [ ] **Step 4: 收尾**

全部通过即完成。若过程中产生过修复提交，确认工作树干净：

```bash
git status
```

Expected: `nothing to commit, working tree clean`（`.output/` 已被 `.gitignore` 忽略，无需提交产物）。

---

## Self-Review（已核对）

- **Spec 覆盖**：§4.1→T1；类型→T2；纯逻辑→T3；§4.6→T4；§4.3→T5；§4.2→T6；§4.5→T7；§4.4→T8；§5/§6→T6 守卫逻辑 + T9 手动矩阵。无遗漏。
- **占位符**：无 TBD/TODO；每个改动均给出完整代码与确切命令。
- **类型一致**：`ReadingSessionResult.reason?`（T2 定义 → T5 返回 → T6 读取）；`StartReadingSessionOptions`（T2 → T3 常量 → T6 使用）；`autoEnterReadingMode` key 在 storage（T1）/getOptions（T6）/chrome.storage 字面量（T7）/saveOptions（T8）一致；函数名 `injectReadingSession`、`setupAutoEnterReadingMode`、`isNavigationResetEvent`、`isEnterCandidateEvent`、`AUTO_ENTER_INJECT_OPTS`、`isArticleLike`、`createAutoEnterToggle`、`getStoredAutoEnter`、`setStoredAutoEnter`、`getSyncStorage` 全程一致；i18n key（T4）与使用处（T7/T8）一致。
