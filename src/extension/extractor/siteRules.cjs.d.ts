export type SiteRule = {
  readable?: boolean;
  contentType?: 'article' | 'qa' | 'discussion' | string;
  titleElem?: string;
  contentElem?: string | string[];
  extractElems?: string[];
  extractElemsJoiner?: string;
  excludeElems?: string[];
  ignoreElements?: string[];
  authorName?: string[];
};

export const SITE_RULES: Record<string, SiteRule>;
export function getSiteRule(
  url: string,
  siteRules?: Record<string, SiteRule>,
): SiteRule | undefined;
export function isReadableUrl(
  url: string,
  siteRules?: Record<string, SiteRule>,
): boolean;
export function urlMatchesRule(url: string, pattern: string): boolean;
