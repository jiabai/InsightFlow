import type { StartReadingSessionOptions } from '@/immersive/readingSession.cjs'

/**
 * 自动进入深度阅读模式时传给 startReadingSession 的注入参数。
 * 加强门槛：仅在「更像正文」且正文足够长时才自动进入（手动点击不受影响）。
 */
export const AUTO_ENTER_INJECT_OPTS: StartReadingSessionOptions = {
  requireArticleLike: true,
  minContentLength: 1500,
}

/**
 * 「自动进入」URL 黑名单：命中的页面即使通过 requireArticleLike 正文启发式也不自动进入。
 * 针对搜索结果 / 代码托管等导航类页面——它们常带 <main> 和大量文本，会骗过正文门槛。
 * 仅作用于「自动」路径；手动点击工具栏图标不受影响，仍可在这些站点进入。
 * 模式语义与 SITE_RULES 的 key 一致：含 `*` 走通配，否则子串匹配（见下方 matchesUrlPattern）。
 */
export const AUTO_ENTER_URL_BLOCKLIST: readonly string[] = [
  'bing.com/',        // 必应搜索（含 cn.bing.com）
  'www.baidu.com/',   // 百度搜索 / 首页（不含 baike.baidu.com 等内容子域）
  'github.com/',      // GitHub：仓库浏览 / 代码 / 搜索（issues、discussions 仍可手动进入）
  'google.*/search',  // 谷歌搜索结果页（含 .com 与各国 ccTLD；放行 maps/scholar 等）
  'duckduckgo.com/',  // DuckDuckGo（纯搜索域）
  'sogou.com/',       // 搜狗搜索（搜索结果页；其指向的微信文章在 mp.weixin.qq.com，不受影响）
  'www.so.com/',      // 360 搜索
]

/**
 * URL 是否在「自动进入」黑名单中。命中 → 跳过自动进入（手动点击不受影响）。
 */
export function isAutoEnterBlockedUrl(
  url: string | undefined,
  blocklist: readonly string[] = AUTO_ENTER_URL_BLOCKLIST,
): boolean {
  if (!url) return false
  return blocklist.some((pattern) => matchesUrlPattern(url, pattern))
}

/**
 * 子串匹配 URL；模式含 `*` 时按通配处理（与 SITE_RULES key 语义一致）。
 * 自包含实现，避免从 siteRules.cjs 跨模块引入类型。
 */
function matchesUrlPattern(url: string, pattern: string): boolean {
  if (!url || !pattern) return false
  if (pattern.includes('*')) {
    return new RegExp(pattern.split('*').map(escapeRegExp).join('.*?')).test(url)
  }
  return url.includes(pattern)
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
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
