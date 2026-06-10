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
  static extractFromDOM(doc) {
    // Step 1: CSS selectors
    for (const selector of SELECTORS) {
      const el = doc.querySelector(selector);
      if (el) {
        const text = getCleanText(el);
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
      const text = getCleanText(child);
      if (text.length > bestLen && text.length >= MIN_CONTENT_LENGTH) {
        bestLen = text.length;
        best = text;
      }
    }

    if (best) {
      return { content: best, method: 'heuristic' };
    }

    // Step 3: Body fallback
    const bodyText = getCleanText(body);
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

function getCleanText(element) {
  // Clone to avoid mutating the original DOM
  const clone = element.cloneNode(true);
  // Remove inline noise
  clone.querySelectorAll('script, style, noscript, iframe, svg').forEach(el => el.remove());
  return (clone.textContent || '').replace(/\s+/g, ' ').trim();
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

module.exports = { ContentExtractor };
