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
