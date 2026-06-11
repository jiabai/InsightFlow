export type ReadingSessionResult =
  | { ok: true; length: number; method: string }
  | { ok: false; error: string };

export type SiteRuleMap = Record<string, unknown>;

export function startReadingSession(siteRules?: SiteRuleMap | null): ReadingSessionResult;
