/**
 * ContentExtractor — extracts main content from HTML pages.
 *
 * Pure function, no browser API dependency.
 * Three-step strategy:
 *   1. CSS selector matching (semantic tags)
 *   2. Heuristic analysis (longest text block)
 *   3. Body fallback (with warning)
 */

const MIN_CONTENT_LENGTH = 100;
const { SITE_RULES, getSiteRule } = require('./siteRules.cjs');

// Noise tags whose content should never be selected as primary content.
const NOISE_TAGS = new Set([
  'SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT',
  'NAV', 'HEADER', 'FOOTER', 'ASIDE', 'IFRAME',
  'SVG', 'FORM', 'BUTTON', 'TEMPLATE',
]);

// Noise class/id substrings to exclude from heuristics.
const NOISE_PATTERNS = [
  'nav', 'header', 'footer', 'sidebar', 'advertisement',
  'ad-', 'banner', 'menu', 'comment', 'related',
  'promo', 'social', 'share', 'widget',
];

const SELECTORS = [
  'main',
  'article',
  '#main-content',
  '.main-content',
  '.post-content',
  '#content',
  'div[role="main"]',
  '.article-content',
  '.blog-post',
  '.entry-content',
  '#article',
  '.Post-RichText',        // Zhihu
  '.rich_media_content',   // WeChat public account
  '.article-body',         // Various CMS
  '.markdown-body',        // GitHub / doc sites
];

class ContentExtractor {
  /**
   * Extract main content from a DOM Document.
   *
   * @param {Document} doc - JSDOM or browser Document
   * @returns {{ content: string, method: string, error?: string }}
   */
  static extractFromDOM(doc, options = {}) {
    // Step 0: Handle iframe content — extract from embedded iframe document
    const iframeDoc = getIframeDocument(doc);
    if (iframeDoc) {
      const result = this._extract(iframeDoc, options);
      if (result.content.length >= MIN_CONTENT_LENGTH) {
        return { ...result, method: 'iframe-' + result.method };
      }
    }

    return this._extract(doc, options);
  }

  /** Internal extraction logic */
  static _extract(doc, options = {}) {
    const siteRule = getRuleForDocument(doc, options);
    if (siteRule?.readable === false) {
      return {
        content: '',
        method: 'unsupported',
        error: 'Current site is marked as not readable',
      };
    }

    const siteRuleResult = extractBySiteRule(doc, siteRule);
    if (siteRuleResult && siteRuleResult.content.length >= MIN_CONTENT_LENGTH) {
      return siteRuleResult;
    }

    // Step 1: CSS selectors
    for (const selector of SELECTORS) {
      const el = doc.querySelector(selector);
      if (el) {
        const text = getCleanText(el, siteRule);
        if (text.length >= MIN_CONTENT_LENGTH) {
          return { content: text, method: 'selector' };
        }
      }
    }

    // Step 2: Heuristic — find longest direct child of body
    const body = doc.body;
    if (!body) {
      return { content: '', method: 'none', error: '页面没有 body 元素' };
    }

    let best = null;
    let bestLen = 0;
    for (const child of body.children) {
      if (isNoiseElement(child)) continue;
      const text = getCleanText(child, siteRule);
      if (text.length > bestLen && text.length >= MIN_CONTENT_LENGTH) {
        bestLen = text.length;
        best = text;
      }
    }

    if (best) {
      return { content: best, method: 'heuristic' };
    }

    // Step 3: Body fallback
    const bodyText = getCleanText(body, siteRule);
    if (bodyText.length >= MIN_CONTENT_LENGTH) {
      return { content: bodyText, method: 'fallback' };
    }

    return {
      content: bodyText,
      method: 'none',
      error: '未检测到可提取的内容（页面文本过短）',
    };
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getRuleForDocument(doc, options = {}) {
  const siteRules = options.siteRules || SITE_RULES;
  const url = options.url || doc?.URL || doc?.baseURI || '';
  return getSiteRule(url, siteRules);
}

function extractBySiteRule(doc, siteRule) {
  if (!siteRule || siteRule.readable === false || !siteRule.contentElem) {
    return null;
  }

  const root = pickBestElement(doc, siteRule.contentElem);
  if (!root) {
    return null;
  }

  const extracts = [];
  for (const selector of asArray(siteRule.extractElems)) {
    extracts.push(...querySelectorAllSafe(root, selector));
  }

  if (extracts.length) {
    const content = extracts
      .map((element) => getCleanText(element, siteRule))
      .filter(Boolean)
      .join('\n\n');

    return {
      content,
      method: `site-rule-${siteRule.contentType || 'article'}`,
    };
  }

  return {
    content: getCleanText(root, siteRule),
    method: 'site-rule',
  };
}

function pickBestElement(doc, selectors) {
  const candidates = [];
  for (const selector of asArray(selectors)) {
    candidates.push(...querySelectorAllSafe(doc, selector));
  }

  let best = null;
  let bestLength = 0;
  for (const candidate of candidates) {
    const textLength = (candidate.textContent || '').replace(/\s+/g, ' ').trim().length;
    if (textLength > bestLength) {
      best = candidate;
      bestLength = textLength;
    }
  }

  return best;
}

function querySelectorAllSafe(root, selector) {
  if (!root || !selector) {
    return [];
  }

  try {
    return Array.from(root.querySelectorAll(selector));
  } catch {
    return [];
  }
}

function asArray(value) {
  if (!value) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
}

function getCleanText(element, siteRule = null) {
  // Clone to avoid mutating the original DOM
  const clone = element.cloneNode(true);
  for (const selector of getRemovalSelectors(siteRule)) {
    querySelectorAllSafe(clone, selector).forEach(el => el.remove());
  }
  // Remove inline noise
  clone.querySelectorAll('script, style, noscript, iframe, svg').forEach(el => el.remove());
  return (clone.textContent || '').replace(/\s+/g, ' ').trim();
}

function getRemovalSelectors(siteRule) {
  return [
    ...asArray(siteRule?.excludeElems),
    ...asArray(siteRule?.ignoreElements),
  ];
}

function isNoiseElement(element) {
  const tag = element.tagName.toUpperCase();
  if (NOISE_TAGS.has(tag)) return true;

  const className = (element.className || '').toLowerCase();
  const id = (element.id || '').toLowerCase();

  for (const pattern of NOISE_PATTERNS) {
    if (className.includes(pattern) || id.includes(pattern)) return true;
  }
  return false;
}

/**
 * Attempt to extract the document from an embedded iframe.
 * Useful for pages that wrap content in a same-origin iframe (e.g. some CMS, doc viewers).
 * @param {Document} doc
 * @returns {Document|null}
 */
function getIframeDocument(doc) {
  try {
    const iframes = doc.querySelectorAll('iframe');
    for (const iframe of iframes) {
      if (iframe.contentDocument && iframe.contentDocument.body) {
        const text = (iframe.contentDocument.body.textContent || '').replace(/\s+/g, ' ').trim();
        if (text.length >= 200) {
          return iframe.contentDocument;
        }
      }
    }
  } catch {
    // Cross-origin iframe — silently skip
  }
  return null;
}

module.exports = { ContentExtractor };
