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
