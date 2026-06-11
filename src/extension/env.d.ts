declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '@/immersive/readingSession.cjs' {
  export type ReadingSessionResult =
    | { ok: true; length: number; method: string }
    | { ok: false; error: string };

  export type SiteRuleMap = Record<string, unknown>;

  export function startReadingSession(siteRules?: SiteRuleMap | null): ReadingSessionResult;
}

declare module '@/extractor/siteRules.cjs' {
  export type SiteRule = {
    readable?: boolean;
    contentType?: string;
    titleElem?: string;
    contentElem?: string | string[];
    extractElems?: string[];
    extractElemsJoiner?: string;
    excludeElems?: string[];
    ignoreElements?: string[];
    authorName?: string[];
  };

  export const SITE_RULES: Record<string, SiteRule>;
  export function isReadableUrl(url: string, siteRules?: Record<string, SiteRule>): boolean;
}

declare global {
  interface Window {
    chrome: typeof chrome;
  }
}
