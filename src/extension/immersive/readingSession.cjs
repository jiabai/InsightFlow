function startReadingSession(siteRules = null, options = {}) {
  const requireArticleLike = Boolean(options && options.requireArticleLike === true);
  const minContentLength =
    options && typeof options.minContentLength === 'number' ? options.minContentLength : 500;
  const GENERATE_PORT_NAME = 'insightflow-generate-questions';
  const LEGACY_GENERATE_TYPE = 'INSIGHTFLOW_GENERATE_QUESTIONS';
  const PORT_GENERATE_START_TYPE = 'INSIGHTFLOW_GENERATE_QUESTIONS_START';
  const GENERATE_TIMEOUT_MS = 240000;
  const DEBUG_PREFIX = '[InsightFlow:reader]';
  const readingWindow = window;
  const messages = createMessages();
  const activeSiteRules = normalizeSiteRules(siteRules);
  let questionsMinimizer = null;

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

    if (requireArticleLike && !isArticleLike(extracted)) {
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
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }

  function extractReadableContent(doc) {
    const siteRule = getWebsiteConfig(doc.baseURI || doc.URL || readingWindow.location?.href || '', activeSiteRules);
    if (siteRule?.readable === false) {
      return { html: '', text: '', method: 'unsupported' };
    }

    const siteExtracted = extractBySiteRule(doc, siteRule);
    if (siteExtracted && siteExtracted.text.length >= 100) {
      return siteExtracted;
    }

    const selectors = getContentSelectors(siteRule);

    for (const selector of selectors) {
      const element = querySelectorSafe(doc, selector);
      const extracted = element ? buildExtractedContent(element, 'selector', siteRule) : null;
      if (extracted && extracted.text.length >= 100) return extracted;
    }

    const body = doc.body;
    if (!body) {
      return { html: '', text: '', method: 'none' };
    }

    let best = null;
    for (const child of Array.from(body.children)) {
      if (isNoiseElement(child)) continue;
      const extracted = buildExtractedContent(child, 'heuristic', siteRule);
      if (!best || extracted.text.length > best.text.length) {
        best = extracted;
      }
    }

    if (best && best.text.length >= 100) return best;
    return buildExtractedContent(body, 'fallback', siteRule);
  }

  function isArticleLike(extracted) {
    const pageUrl = document.baseURI || document.URL || readingWindow.location?.href || '';
    const siteRule = getWebsiteConfig(pageUrl, activeSiteRules);
    const hasContentRule = Boolean(siteRule && siteRule.contentElem);
    const hasArticleStructure = Boolean(document.querySelector('article, main, [role="main"]'));
    // 抽取时命中了正文选择器或站点规则，也视为「正文页」（method: 'selector' / 'site-rule*'），
    // 这样像 news.qq.com 这种无语义标签、但正文在 .rich_media_content 等已知容器里的页面也能自动进入。
    const method = extracted && extracted.method;
    const matchedContentSelector =
      method === 'selector' || (typeof method === 'string' && method.startsWith('site-rule'));
    return hasContentRule || hasArticleStructure || matchedContentSelector;
  }

  function extractBySiteRule(doc, siteRule) {
    if (!siteRule || !siteRule.contentElem) {
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
      const wrapper = doc.createElement('div');
      const contentType = siteRule.contentType || 'article';
      wrapper.innerHTML = extracts
        .map((element, index) => {
          return `<div class="insight-flow-${contentType} insight-flow-${contentType}-${index}">${element.innerHTML}</div>`;
        })
        .join(siteRule.extractElemsJoiner || '');

      return buildExtractedContent(wrapper, `site-rule-${contentType}`, siteRule);
    }

    return buildExtractedContent(root, 'site-rule', siteRule);
  }

  function getContentSelectors(siteRule) {
    return [
      ...asArray(siteRule?.contentElem),
      '#js_content',
      '.rich_media_content',
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
      '.Post-RichText',
      '.article-body',
      '.markdown-body',
    ];
  }

  function pickBestElement(root, selectors) {
    const candidates = [];
    for (const selector of asArray(selectors)) {
      candidates.push(...querySelectorAllSafe(root, selector));
    }

    let best = null;
    let bestLength = 0;
    for (const candidate of candidates) {
      const length = getCleanText(candidate).length;
      if (length > bestLength) {
        best = candidate;
        bestLength = length;
      }
    }

    return best;
  }

  function buildExtractedContent(element, method, siteRule = null) {
    const clone = sanitizeClone(element, siteRule);
    const title = getPageTitle(siteRule);
    const text = getCleanText(clone);

    if (title && !text.includes(title)) {
      const heading = document.createElement('h1');
      heading.textContent = title;
      clone.prepend(heading);
    }

    return {
      html: clone.innerHTML,
      text: getCleanText(clone),
      method,
    };
  }

  function sanitizeClone(element, siteRule = null) {
    const clone = element.cloneNode(true);

    for (const selector of getRemovalSelectors(siteRule)) {
      querySelectorAllSafe(clone, selector).forEach((node) => node.remove());
    }

    clone
      .querySelectorAll('script, style, noscript, iframe, svg, form, button, input, textarea, select')
      .forEach((node) => node.remove());

    clone.querySelectorAll('img').forEach(normalizeImage);
    clone.querySelectorAll('source').forEach(normalizeSource);

    clone.querySelectorAll('*').forEach((node) => {
      for (const attribute of Array.from(node.attributes)) {
        const name = attribute.name.toLowerCase();
        const value = attribute.value.trim();

        if (name.startsWith('on') || name === 'style') {
          node.removeAttribute(attribute.name);
          continue;
        }

        if ((name === 'href' || name === 'src') && /^javascript:/i.test(value)) {
          node.removeAttribute(attribute.name);
          continue;
        }

        if ((name === 'href' || name === 'src') && value && !value.startsWith('#')) {
          try {
            node.setAttribute(attribute.name, new URL(value, document.baseURI).href);
          } catch {
            node.removeAttribute(attribute.name);
          }
          continue;
        }

        if (!isContentAttribute(name)) {
          node.removeAttribute(attribute.name);
        }
      }
    });

    return clone;
  }

  function normalizeImage(image) {
    const lazySrc = getFirstAttribute(image, [
      'data-src',
      'data-original',
      'data-original-src',
      'data-backsrc',
      'data-croporisrc',
      'data-lazy-src',
      'data-actualsrc',
      'data-url',
    ]);
    if (lazySrc) {
      image.setAttribute('src', lazySrc);
    }

    const lazySrcset = getFirstAttribute(image, ['data-srcset', 'data-original-srcset', 'data-lazy-srcset']);
    if (lazySrcset) {
      image.setAttribute('srcset', lazySrcset);
    } else if (lazySrc) {
      image.removeAttribute('srcset');
    }

    image.setAttribute('loading', 'lazy');
    image.setAttribute('decoding', 'async');
  }

  function normalizeSource(source) {
    const lazySrcset = getFirstAttribute(source, ['data-srcset', 'data-original-srcset', 'data-lazy-srcset']);
    if (lazySrcset) {
      source.setAttribute('srcset', lazySrcset);
    }
  }

  function getFirstAttribute(element, names) {
    for (const name of names) {
      const value = element.getAttribute(name);
      if (value && value.trim()) {
        return value.trim();
      }
    }
    return '';
  }

  function isContentAttribute(name) {
    return [
      'alt',
      'colspan',
      'decoding',
      'height',
      'href',
      'loading',
      'media',
      'poster',
      'rel',
      'rowspan',
      'src',
      'srcset',
      'target',
      'title',
      'type',
      'width',
    ].includes(name);
  }

  function getPageTitle(siteRule = null) {
    const titleElement =
      querySelectorSafe(document, siteRule?.titleElem) ||
      document.querySelector('#activity-name') ||
      document.querySelector('h1') ||
      document.querySelector('title');
    return (titleElement?.textContent || document.title || '').replace(/\s+/g, ' ').trim();
  }

  function getCleanText(element) {
    return (element.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function getWebsiteConfig(url, rules) {
    if (!rules) return {};
    const sourceUrl = String(url || '');
    const key = Object.keys(rules).find((pattern) => urlMatchesRule(sourceUrl, pattern));
    return key ? rules[key] : {};
  }

  function urlMatchesRule(url, pattern) {
    if (!url || !pattern) return false;
    if (pattern.includes('*')) {
      return wildcardPatternToRegExp(pattern).test(url);
    }
    return url.includes(pattern);
  }

  function wildcardPatternToRegExp(pattern) {
    return new RegExp(pattern.split('*').map(escapeRegExp).join('.*?'));
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function querySelectorSafe(root, selector) {
    if (!root || !selector) return null;
    try {
      return root.querySelector(selector);
    } catch {
      return null;
    }
  }

  function querySelectorAllSafe(root, selector) {
    if (!root || !selector) return [];
    try {
      return Array.from(root.querySelectorAll(selector));
    } catch {
      return [];
    }
  }

  function asArray(value) {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  }

  function getRemovalSelectors(siteRule) {
    return [
      ...asArray(siteRule?.excludeElems),
      ...asArray(siteRule?.ignoreElements),
    ];
  }

  function normalizeSiteRules(rules) {
    return rules && typeof rules === 'object' ? rules : {};
  }

  function isNoiseElement(element) {
    const tag = element.tagName.toUpperCase();
    if (['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'NAV', 'HEADER', 'FOOTER', 'ASIDE'].includes(tag)) {
      return true;
    }

    const marker = `${element.id} ${String(element.className || '')}`.toLowerCase();
    return [
      'nav',
      'header',
      'footer',
      'sidebar',
      'advertisement',
      'ad-',
      'banner',
      'menu',
      'comment',
      'related',
      'promo',
      'social',
      'share',
      'widget',
    ].some((pattern) => marker.includes(pattern));
  }

  function renderReadingSession(extracted) {
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousBodyOverflow = document.body.style.overflow;

    const style = document.createElement('style');
    style.id = 'immersive-reading-style';
    style.textContent = `
      #immersive-container {
        position: fixed !important;
        inset: 0 !important;
        z-index: 2147483647 !important;
        overflow: auto !important;
        background: #303030 !important;
        color: #f5f5f5 !important;
        font-family: "Segoe UI", "Helvetica Neue", Arial, "Microsoft YaHei", sans-serif !important;
      }
      #immersive-container,
      #immersive-container * {
        box-sizing: border-box !important;
      }
      #insight-flow-header {
        position: sticky !important;
        top: 0 !important;
        z-index: 3 !important;
        height: 72px !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 0 max(80px, calc((100vw - 1700px) / 2)) !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.32) !important;
        background: #303030 !important;
        color: #ffffff !important;
      }
      #insight-flow-header .insight-flow-mark {
        width: 28px !important;
        height: 28px !important;
        display: inline-grid !important;
        place-items: center !important;
        color: #75bfff !important;
        font-size: 27px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
      }
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
      #immersive-container .insight-flow-shell {
        width: min(1700px, calc(100vw - 160px)) !important;
        margin: 40px auto 56px !important;
      }
      #immersive-container .insight-flow-reader {
        position: relative !important;
        min-height: calc(100vh - 160px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        background: #050505 !important;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.38) !important;
      }
      #immersive-container .insight-flow-actions {
        position: absolute !important;
        top: 22px !important;
        right: 22px !important;
        z-index: 4 !important;
        display: flex !important;
        gap: 14px !important;
        transform: translate(0, 0) !important;
      }
      #generate-questions,
      #immersive-close {
        appearance: none !important;
        -webkit-appearance: none !important;
        position: relative !important;
        width: 52px !important;
        min-width: 52px !important;
        height: 52px !important;
        min-height: 52px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border-radius: 50% !important;
        color: #050505 !important;
        cursor: pointer !important;
        font-family: "Segoe UI Symbol", "Segoe UI", Arial, sans-serif !important;
        font-size: 0 !important;
        font-weight: 300 !important;
        line-height: 1 !important;
        box-shadow: 0 10px 18px rgba(0, 0, 0, 0.28) !important;
        text-align: center !important;
        text-indent: 0 !important;
        text-transform: none !important;
        user-select: none !important;
      }
      #generate-questions {
        background: #43bf4f !important;
      }
      #immersive-close {
        background: #a52326 !important;
        color: #ffffff !important;
      }
      #generate-questions .insight-flow-action-icon,
      #immersive-close .insight-flow-action-icon {
        position: relative !important;
        width: 24px !important;
        height: 24px !important;
        display: block !important;
        flex: 0 0 24px !important;
        pointer-events: none !important;
      }
      #generate-questions .insight-flow-action-icon::before,
      #generate-questions .insight-flow-action-icon::after,
      #immersive-close .insight-flow-action-icon::before,
      #immersive-close .insight-flow-action-icon::after {
        content: '' !important;
        position: absolute !important;
        left: 50% !important;
        top: 50% !important;
        width: 24px !important;
        height: 3px !important;
        border-radius: 999px !important;
        background: currentColor !important;
        transform-origin: center !important;
      }
      #generate-questions .insight-flow-action-icon::before {
        transform: translate(-50%, -50%) !important;
      }
      #generate-questions .insight-flow-action-icon::after {
        transform: translate(-50%, -50%) rotate(90deg) !important;
      }
      #immersive-close .insight-flow-action-icon::before {
        transform: translate(-50%, -50%) rotate(45deg) !important;
      }
      #immersive-close .insight-flow-action-icon::after {
        transform: translate(-50%, -50%) rotate(-45deg) !important;
      }
      #generate-questions[disabled] {
        cursor: wait !important;
        filter: grayscale(0.2) brightness(0.85) !important;
      }
      #generate-questions::before,
      #immersive-close::before {
        position: absolute !important;
        left: 50% !important;
        bottom: calc(100% + 12px) !important;
        transform: translateX(-50%) !important;
        display: none !important;
        width: max-content !important;
        max-width: 240px !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        background: #050505 !important;
        color: #ffffff !important;
        content: attr(data-tooltip) !important;
        font-size: 22px !important;
        font-weight: 400 !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35) !important;
      }
      #generate-questions:hover::before,
      #generate-questions:focus-visible::before,
      #immersive-close:hover::before,
      #immersive-close:focus-visible::before {
        display: block !important;
      }
      #immersive-content-area {
        width: 100% !important;
        max-width: none !important;
        margin: 0 auto !important;
        padding: 30px 96px 80px !important;
        background: #050505 !important;
        color: #eeeeee !important;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif !important;
        font-size: 22px !important;
        line-height: 1.66em !important;
      }
      #immersive-content-area .insight-flow-article {
        margin-top: 0 !important;
        padding-bottom: 64px !important;
        line-height: 1.66em !important;
      }
      #immersive-content-area .insight-flow-article * {
        max-width: 100% !important;
        letter-spacing: 0em !important;
        text-shadow: none !important;
      }
      #immersive-content-area p,
      #immersive-content-area div,
      #immersive-content-area section {
        background: transparent !important;
        min-height: 0 !important;
      }
      #immersive-content-area h1 {
        margin: 0 0 0.8em !important;
        color: #f4f4f4 !important;
        font-family: inherit !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        line-height: 1.3em !important;
        text-align: left !important;
      }
      #immersive-content-area h1:not(:first-child) {
        margin-top: 1.6em !important;
      }
      #immersive-content-area h2 {
        margin: 1.6em 0 0.8em !important;
        color: #f0f0f0 !important;
        font-family: inherit !important;
        font-size: 1.375rem !important;
        font-weight: 700 !important;
        line-height: 1.5em !important;
      }
      #immersive-content-area h3 {
        margin: 1.6em 0 0.8em !important;
        color: #f0f0f0 !important;
        font-family: inherit !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        line-height: 1.5em !important;
      }
      #immersive-content-area h4 {
        margin: 1.6em 0 0.8em !important;
        color: #f0f0f0 !important;
        font-family: inherit !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        line-height: 1.5em !important;
      }
      #immersive-content-area h5 {
        margin: 1.6em 0 0.8em !important;
        color: #f0f0f0 !important;
        font-family: inherit !important;
        font-size: 0.875rem !important;
        font-weight: 700 !important;
        line-height: 1.5em !important;
      }
      #immersive-content-area h6 {
        margin: 1.6em 0 0.8em !important;
        color: #f0f0f0 !important;
        font-family: inherit !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        line-height: 1.5em !important;
      }
      #immersive-content-area p,
      #immersive-content-area li {
        color: #efefef !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
      }
      #immersive-content-area p {
        position: relative !important;
        margin-top: 1.24em !important;
        margin-bottom: 1.24em !important;
        line-height: 1.66em !important;
        word-break: break-word !important;
      }
      #immersive-content-area div {
        color: #efefef !important;
        font-size: 1rem !important;
        line-height: 1.66em !important;
      }
      #immersive-content-area ul,
      #immersive-content-area ol {
        margin: 1.18em 0 !important;
        padding-left: 1.1em !important;
      }
      #immersive-content-area ol {
        list-style-type: decimal !important;
      }
      #immersive-content-area li {
        margin-bottom: 0 !important;
        line-height: 1.59em !important;
      }
      #immersive-content-area li p {
        margin: 0.5em 0 !important;
      }
      #immersive-content-area strong,
      #immersive-content-area b {
        color: #ffffff !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
      }
      #immersive-content-area a {
        color: #8ecaff !important;
        text-decoration: none !important;
        border-bottom: 1px dashed rgba(142, 202, 255, 0.72) !important;
      }
      #immersive-content-area a:hover {
        border-bottom: 2px solid #8ecaff !important;
      }
      #immersive-content-area img,
      #immersive-content-area svg,
      #immersive-content-area video {
        display: block !important;
        max-width: 100% !important;
        height: auto !important;
        margin: 12px auto !important;
      }
      #immersive-content-area figure {
        margin: 1.6em 0 !important;
        padding: 0 !important;
        text-align: center !important;
      }
      #immersive-content-area figcaption {
        font-size: 0.875rem !important;
        opacity: 0.6 !important;
        text-align: center !important;
      }
      #immersive-content-area table {
        margin: 1em !important;
        border-collapse: collapse !important;
        border-spacing: 0 !important;
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        line-height: 1.18em !important;
        font-size: 1rem !important;
      }
      #immersive-content-area th {
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        padding: 8px !important;
        font-size: 1rem !important;
      }
      #immersive-content-area td {
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        padding: 8px !important;
        font-size: 0.875rem !important;
      }
      #immersive-content-area td * {
        font-size: 0.875rem !important;
        word-break: break-all !important;
      }
      #immersive-content-area tr:nth-child(odd) {
        background-color: rgba(255, 255, 255, 0.04) !important;
      }
      #immersive-content-area blockquote {
        margin: 1.6em 0 !important;
        padding: 0.2em 0 0.2em 1.1em !important;
        border-left: 4px solid #43bf4f !important;
        color: #d8d8d8 !important;
      }
      #immersive-content-area blockquote p {
        line-height: 1.59em !important;
      }
      #immersive-content-area pre {
        overflow: auto !important;
        margin: 2em 0 3.2em !important;
        padding: 1em !important;
        border-radius: 10px !important;
        background: #111111 !important;
        font-family: Menlo, Monaco, "Courier New", Courier, monospace !important;
        font-size: 0.875rem !important;
        line-height: 1.4em !important;
        white-space: pre-wrap !important;
        word-break: break-all !important;
        word-wrap: break-word !important;
      }
      #immersive-content-area code {
        font-family: Menlo, Monaco, "Courier New", Courier, monospace !important;
        font-size: 1rem !important;
        padding: 2px 4px !important;
        background: #111111 !important;
        color: #eeeeee !important;
      }
      #question-sidebar {
        display: none !important;
        position: fixed !important;
        top: 96px !important;
        right: max(24px, calc((100vw - 1700px) / 2 + 24px)) !important;
        z-index: 6 !important;
        width: min(380px, calc(100vw - 48px)) !important;
        max-height: calc(100vh - 120px) !important;
        overflow: auto !important;
        margin: 0 !important;
        padding: 18px 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 8px !important;
        background: #0f0f0f !important;
        color: #eeeeee !important;
        box-shadow: 0 18px 38px rgba(0, 0, 0, 0.42) !important;
        cursor: grab !important;
        transform-origin: top right !important;
        transition: transform 0.27s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease !important;
      }
      #question-sidebar.is-active {
        display: block !important;
      }
      #question-sidebar.is-dragging,
      #question-sidebar.is-dragging * {
        cursor: grabbing !important;
        user-select: none !important;
      }
      #question-sidebar .question-title {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        margin: 0 0 12px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        cursor: grab !important;
        user-select: none !important;
      }
      #question-sidebar .question-title-text {
        flex: 1 1 auto !important;
        min-width: 0 !important;
      }
      #question-sidebar .question-minimize {
        flex: 0 0 auto !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        width: 28px !important;
        height: 28px !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 6px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        color: #eeeeee !important;
        cursor: pointer !important;
        transition: background 0.18s ease, border-color 0.18s ease !important;
      }
      #question-sidebar .question-minimize:hover {
        background: rgba(67, 191, 79, 0.16) !important;
        border-color: rgba(67, 191, 79, 0.6) !important;
      }
      #question-sidebar .question-minimize:focus-visible {
        outline: 2px solid #43bf4f !important;
        outline-offset: 2px !important;
      }
      #question-sidebar .question-minimize-bar {
        display: block !important;
        width: 11px !important;
        height: 2px !important;
        border-radius: 2px !important;
        background: currentColor !important;
      }
      #question-sidebar.is-min {
        transform: scale(0.16) !important;
        opacity: 0 !important;
        pointer-events: none !important;
      }
      #question-dot {
        position: fixed !important;
        z-index: 7 !important;
        box-sizing: border-box !important;
        width: 40px !important;
        height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 50% !important;
        border: 1px solid rgba(67, 191, 79, 0.7) !important;
        background: #0f0f0f !important;
        color: #eaeaea !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        cursor: grab !important;
        user-select: none !important;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4) !important;
        transform-origin: top right !important;
        transition: transform 0.27s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease, background 0.18s ease !important;
      }
      #question-dot:hover {
        background: rgba(67, 191, 79, 0.18) !important;
      }
      #question-dot:focus-visible {
        outline: 2px solid #43bf4f !important;
        outline-offset: 2px !important;
      }
      #question-dot.is-dragging {
        cursor: grabbing !important;
      }
      #question-dot.is-hidden {
        transform: scale(0.2) !important;
        opacity: 0 !important;
        pointer-events: none !important;
      }
      #question-dot .question-dot-face {
        pointer-events: none !important;
      }
      #question-dot .question-dot-badge {
        position: absolute !important;
        top: -5px !important;
        right: -5px !important;
        box-sizing: border-box !important;
        min-width: 18px !important;
        height: 18px !important;
        padding: 0 4px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 9px !important;
        background: #43bf4f !important;
        color: #0b2e10 !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        pointer-events: none !important;
      }
      #question-sidebar .question-card {
        position: relative !important;
        margin: 10px 0 !important;
        padding: 12px 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 6px !important;
        background: #111111 !important;
        color: #eeeeee !important;
        font-size: 16px !important;
        line-height: 1.45 !important;
        cursor: pointer !important;
        user-select: none !important;
        transition: border-color 0.15s ease, background 0.15s ease, transform 0.05s ease !important;
      }
      #question-sidebar .question-card * {
        cursor: pointer !important;
        user-select: none !important;
        pointer-events: none !important;
      }
      #question-sidebar .question-card:hover {
        border-color: rgba(67, 191, 79, 0.6) !important;
        background: #161616 !important;
      }
      #question-sidebar .question-card:active {
        transform: scale(0.99) !important;
      }
      #question-sidebar .question-card:focus-visible {
        outline: 2px solid #43bf4f !important;
        outline-offset: 2px !important;
      }
      #question-sidebar .question-card.is-copied {
        border-color: #43bf4f !important;
        background: rgba(67, 191, 79, 0.12) !important;
      }
      #question-sidebar .question-card.is-copy-failed {
        border-color: #a52326 !important;
        background: rgba(165, 35, 38, 0.14) !important;
      }
      #question-sidebar .question-card.is-copied::after,
      #question-sidebar .question-card.is-copy-failed::after {
        content: attr(data-copy-feedback) !important;
        position: absolute !important;
        top: 8px !important;
        right: 10px !important;
        padding: 2px 8px !important;
        border-radius: 999px !important;
        background: #050505 !important;
        color: #ffffff !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        line-height: 1.5 !important;
        white-space: nowrap !important;
        pointer-events: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
      }
      #question-sidebar .question-card.is-copied::after {
        color: #8ff0a0 !important;
      }
      #question-sidebar .question-card.is-copy-failed::after {
        color: #ff9ea0 !important;
      }
      @media (max-width: 900px) {
        #insight-flow-header {
          height: 60px !important;
          padding: 0 18px !important;
        }
        #immersive-container .insight-flow-shell {
          width: calc(100vw - 24px) !important;
          margin: 24px auto !important;
        }
        #immersive-container .insight-flow-actions {
          gap: 8px !important;
        }
        #generate-questions,
        #immersive-close {
          width: 48px !important;
          min-width: 48px !important;
          height: 48px !important;
          min-height: 48px !important;
        }
        #generate-questions .insight-flow-action-icon,
        #immersive-close .insight-flow-action-icon {
          width: 22px !important;
          height: 22px !important;
          flex-basis: 22px !important;
        }
        #generate-questions .insight-flow-action-icon::before,
        #generate-questions .insight-flow-action-icon::after,
        #immersive-close .insight-flow-action-icon::before,
        #immersive-close .insight-flow-action-icon::after {
          width: 22px !important;
          height: 3px !important;
        }
        #immersive-content-area {
          max-width: 100% !important;
          padding: 36px 22px 42px !important;
          font-size: 18px !important;
        }
        #immersive-content-area .insight-flow-article {
          margin-top: 1em !important;
          padding-bottom: 42px !important;
        }
        #question-sidebar {
          top: 88px !important;
          right: 16px !important;
          left: 16px !important;
          width: auto !important;
          max-height: min(52vh, 460px) !important;
        }
      }
      #question-sidebar .insight-flow-loading-status {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        margin: 2px 0 14px !important;
        color: #d6d6d6 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
      }
      #question-sidebar .insight-flow-spinner {
        flex: 0 0 16px !important;
        width: 16px !important;
        height: 16px !important;
        border: 2px solid rgba(255, 255, 255, 0.25) !important;
        border-top-color: #43bf4f !important;
        border-radius: 50% !important;
        animation: insight-flow-spin 0.8s linear infinite !important;
      }
      #question-sidebar .insight-flow-skeleton {
        margin-top: 4px !important;
      }
      #question-sidebar .insight-flow-skeleton-card {
        margin: 10px 0 !important;
        padding: 12px 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 6px !important;
        background: #111111 !important;
      }
      #question-sidebar .insight-flow-skeleton-line {
        height: 12px !important;
        margin: 9px 0 !important;
        border-radius: 6px !important;
        background: linear-gradient(90deg, #1c1c1c 25%, #2e2e2e 50%, #1c1c1c 75%) !important;
        background-size: 200% 100% !important;
        animation: insight-flow-shimmer 1.4s linear infinite !important;
      }
      #question-sidebar .insight-flow-skeleton-line.title {
        width: 62% !important;
        height: 15px !important;
        margin-bottom: 12px !important;
      }
      #question-sidebar .insight-flow-skeleton-line.short {
        width: 44% !important;
      }
      @keyframes insight-flow-spin {
        to { transform: rotate(360deg); }
      }
      @keyframes insight-flow-shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `;

    const container = document.createElement('div');
    container.id = 'immersive-container';
    container.setAttribute('role', 'dialog');
    container.setAttribute('aria-modal', 'true');
    container.setAttribute('aria-label', messages.immersiveReadingLabel);

    const header = document.createElement('header');
    header.id = 'insight-flow-header';

    const mark = document.createElement('span');
    mark.className = 'insight-flow-mark';
    mark.textContent = '⌘';

    const wordmark = document.createElement('span');
    wordmark.className = 'insight-flow-wordmark';
    wordmark.textContent = 'InsightFlow';

    const autoToggle = createAutoEnterToggle();

    header.append(mark, wordmark, autoToggle);

    const shell = document.createElement('div');
    shell.className = 'insight-flow-shell';

    const reader = document.createElement('section');
    reader.className = 'insight-flow-reader';

    const actions = document.createElement('div');
    actions.className = 'insight-flow-actions';

    const generateButton = document.createElement('button');
    generateButton.id = 'generate-questions';
    generateButton.type = 'button';
    generateButton.dataset.tooltip = messages.generateQuestions;
    generateButton.setAttribute('aria-label', messages.generateQuestions);
    generateButton.append(createActionIcon());

    const closeButton = document.createElement('button');
    closeButton.id = 'immersive-close';
    closeButton.type = 'button';
    closeButton.dataset.tooltip = messages.exitReadingMode;
    closeButton.setAttribute('aria-label', messages.exitReadingMode);
    closeButton.append(createActionIcon());

    actions.append(generateButton, closeButton);

    const content = document.createElement('main');
    content.id = 'immersive-content-area';

    const article = document.createElement('article');
    article.className = 'insight-flow-article';
    article.setAttribute('dir', 'auto');
    article.innerHTML = extracted.html;
    content.append(article);

    const sidebar = document.createElement('aside');
    sidebar.id = 'question-sidebar';
    sidebar.setAttribute('aria-label', messages.questions);
    const cleanupSidebarDragging = setupSidebarDragging(sidebar);

    const questionDot = createQuestionDot();
    questionsMinimizer = createQuestionsMinimizer(sidebar, questionDot);

    reader.append(actions, content, sidebar, questionDot);
    shell.append(reader);
    container.append(header, shell);

    const cleanup = () => {
      cleanupSidebarDragging();
      if (questionsMinimizer) {
        questionsMinimizer.cleanup();
        questionsMinimizer = null;
      }
      style.remove();
      container.remove();
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.body.style.overflow = previousBodyOverflow;
      window.removeEventListener('keydown', onKeyDown, true);
      delete readingWindow.__insightFlowReadingSessionCleanup;
    };

    const onKeyDown = (event) => {
      if (event.key === 'Escape') cleanup();
    };

    closeButton.addEventListener('click', cleanup);
    generateButton.addEventListener('click', () => {
      const requestId = createRequestId();
      debugLog('generate:click', {
        requestId,
        contentLength: extracted.text.length,
      });
      generateQuestions(extracted.text, sidebar, generateButton, requestId);
    });
    window.addEventListener('keydown', onKeyDown, true);
    readingWindow.__insightFlowReadingSessionCleanup = cleanup;

    document.head.append(style);
    document.body.append(container);
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
  }

  function generateQuestions(content, sidebar, button, requestId) {
    button.disabled = true;
    renderSidebarLoading(sidebar, `${messages.generatingQuestions} (${shortRequestId(requestId)})`);
    debugLog('generate:content-ready', {
      requestId,
      contentLength: content.length,
    });

    requestQuestionGeneration(content, requestId)
      .then((response) => {
        if (!response || response.ok === false) {
          throw new Error(response?.error || messages.failedToGenerateQuestions);
        }
        debugLog('generate:success', {
          requestId: response.requestId || requestId,
          questionsCount: Array.isArray(response.questions) ? response.questions.length : 0,
        });
        renderQuestions(sidebar, response.questions || []);
      })
      .catch((error) => {
        debugError('generate:error', error, { requestId });
        renderSidebarStatus(sidebar, error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        button.disabled = false;
      });
  }

  function requestQuestionGeneration(content, requestId) {
    const runtime =
      (window.chrome && window.chrome.runtime) ||
      (globalThis.chrome && globalThis.chrome.runtime);

    if (!runtime || (typeof runtime.connect !== 'function' && typeof runtime.sendMessage !== 'function')) {
      return Promise.reject(new Error(messages.extensionMessagingUnavailable));
    }

    if (typeof runtime.connect === 'function') {
      return requestQuestionGenerationViaPort(runtime, content, requestId);
    }

    return requestQuestionGenerationViaLegacyMessage(runtime, content, requestId);
  }

  function requestQuestionGenerationViaPort(runtime, content, requestId) {
    return new Promise((resolve, reject) => {
      let settled = false;
      let port;
      let timeoutId;

      const settle = (callback) => {
        if (settled) return;
        settled = true;
        if (timeoutId) clearTimeout(timeoutId);
        try {
          port?.disconnect();
        } catch {
          // The port may already be closed by the service worker.
        }
        callback();
      };

      const finish = (response) => {
        settle(() => resolve(response));
      };

      try {
        debugLog('port:connect', { requestId, portName: GENERATE_PORT_NAME });
        port = runtime.connect({ name: GENERATE_PORT_NAME });

        port.onMessage.addListener((response) => {
          debugLog('port:message', {
            requestId: response?.requestId || requestId,
            ok: response?.ok,
            questionsCount: Array.isArray(response?.questions) ? response.questions.length : undefined,
            error: response?.error,
          });
          finish(response);
        });

        port.onDisconnect.addListener(() => {
          const lastError = runtime.lastError;
          debugLog('port:disconnect', {
            requestId,
            error: lastError?.message,
          });
          if (!settled) {
            settle(() => reject(new Error(lastError?.message || messages.failedToGenerateQuestions)));
          }
        });

        timeoutId = setTimeout(() => {
          debugLog('generate:timeout', {
            requestId,
            timeoutMs: GENERATE_TIMEOUT_MS,
          });
          settle(() => reject(new Error(`${messages.failedToGenerateQuestions} (${shortRequestId(requestId)} timeout)`)));
        }, GENERATE_TIMEOUT_MS);

        debugLog('port:post-start', {
          requestId,
          contentLength: content.length,
        });
        port.postMessage({
          type: PORT_GENERATE_START_TYPE,
          requestId,
          contentLength: content.length,
          content,
        });
      } catch (error) {
        settle(() => reject(error));
      }
    });
  }

  function requestQuestionGenerationViaLegacyMessage(runtime, content, requestId) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const finish = (response) => {
        if (settled) return;
        settled = true;
        const lastError = runtime.lastError;
        if (lastError) {
          reject(new Error(lastError.message || String(lastError)));
          return;
        }
        resolve(response);
      };

      try {
        debugLog('legacy-message:post-start', {
          requestId,
          contentLength: content.length,
        });
        const maybePromise = runtime.sendMessage(
          {
            type: LEGACY_GENERATE_TYPE,
            requestId,
            contentLength: content.length,
            content,
          },
          finish,
        );
        if (maybePromise && typeof maybePromise.then === 'function') {
          maybePromise.then(finish, reject);
        }
      } catch (error) {
        reject(error);
      }
    });
  }

  function createRequestId() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  function shortRequestId(requestId) {
    return String(requestId || '').slice(-6) || 'unknown';
  }

  function serializeError(error) {
    if (error instanceof Error) {
      return {
        message: error.message,
        stack: error.stack,
      };
    }
    return { message: String(error) };
  }

  function sanitizeDebugDetails(details) {
    const sanitized = {};
    for (const [key, value] of Object.entries(details || {})) {
      if (key === 'content' && typeof value === 'string') {
        sanitized.contentLength = value.length;
        continue;
      }
      sanitized[key] = value;
    }
    return sanitized;
  }

  function debugLog(event, details = {}) {
    try {
      console.info(DEBUG_PREFIX, event, sanitizeDebugDetails(details));
    } catch {
      // Debug logging must never affect the reading session.
    }
  }

  function debugError(event, error, details = {}) {
    try {
      console.error(DEBUG_PREFIX, event, {
        ...sanitizeDebugDetails(details),
        error: serializeError(error),
      });
    } catch {
      // Debug logging must never affect the reading session.
    }
  }

  function setupSidebarDragging(sidebar) {
    const state = {
      active: false,
      pointerId: null,
      offsetX: 0,
      offsetY: 0,
      previousBodyUserSelect: '',
    };

    const stopDrag = (event = null) => {
      if (!state.active) return;
      if (event && event.pointerId !== state.pointerId) return;

      state.active = false;
      sidebar.classList.remove('is-dragging');
      document.body.style.userSelect = state.previousBodyUserSelect;

      try {
        if (state.pointerId !== null && typeof sidebar.releasePointerCapture === 'function') {
          sidebar.releasePointerCapture(state.pointerId);
        }
      } catch {
        // Pointer capture can already be released by the browser.
      }

      state.pointerId = null;
      document.removeEventListener('pointermove', onPointerMove, true);
      document.removeEventListener('pointerup', onPointerUp, true);
      document.removeEventListener('pointercancel', onPointerUp, true);
    };

    const onPointerMove = (event) => {
      if (!state.active || event.pointerId !== state.pointerId) return;

      const nextPosition = clampSidebarPosition(
        sidebar,
        event.clientX - state.offsetX,
        event.clientY - state.offsetY,
      );

      sidebar.style.left = `${nextPosition.left}px`;
      sidebar.style.top = `${nextPosition.top}px`;
      sidebar.style.right = 'auto';
      event.preventDefault();
    };

    const onPointerUp = (event) => {
      stopDrag(event);
    };

    const onPointerDown = (event) => {
      if (event.pointerType !== 'mouse' || event.button !== 0) return;
      if (!sidebar.classList.contains('is-active')) return;
      if (isSidebarDragBlockedTarget(event.target)) return;

      const rect = sidebar.getBoundingClientRect();
      state.active = true;
      state.pointerId = event.pointerId;
      state.offsetX = event.clientX - rect.left;
      state.offsetY = event.clientY - rect.top;
      state.previousBodyUserSelect = document.body.style.userSelect;

      sidebar.classList.add('is-dragging');
      document.body.style.userSelect = 'none';

      try {
        if (typeof sidebar.setPointerCapture === 'function') {
          sidebar.setPointerCapture(event.pointerId);
        }
      } catch {
        // Pointer capture is an enhancement; document listeners keep dragging working.
      }

      document.addEventListener('pointermove', onPointerMove, true);
      document.addEventListener('pointerup', onPointerUp, true);
      document.addEventListener('pointercancel', onPointerUp, true);
      event.preventDefault();
    };

    sidebar.addEventListener('pointerdown', onPointerDown);

    return () => {
      stopDrag();
      sidebar.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('pointermove', onPointerMove, true);
      document.removeEventListener('pointerup', onPointerUp, true);
      document.removeEventListener('pointercancel', onPointerUp, true);
    };
  }

  function isSidebarDragBlockedTarget(target) {
    if (!target || typeof target.closest !== 'function') return false;

    return Boolean(
      target.closest('.question-card, a, button, input, textarea, select, [contenteditable="true"]'),
    );
  }

  function clampSidebarPosition(sidebar, left, top) {
    const margin = 8;
    const rect = sidebar.getBoundingClientRect();
    const width = rect.width || sidebar.offsetWidth || 320;
    const height = rect.height || sidebar.offsetHeight || 240;
    const maxLeft = Math.max(margin, window.innerWidth - width - margin);
    const maxTop = Math.max(margin, window.innerHeight - height - margin);

    return {
      left: Math.min(Math.max(left, margin), maxLeft),
      top: Math.min(Math.max(top, margin), maxTop),
    };
  }

  function renderSidebarStatus(sidebar, message) {
    sidebar.classList.add('is-active');
    sidebar.textContent = '';

    const title = document.createElement('div');
    title.className = 'question-title';
    title.textContent = message;
    sidebar.append(title);
  }

  function renderSidebarLoading(sidebar, message) {
    sidebar.classList.add('is-active');
    sidebar.textContent = '';
    if (questionsMinimizer) questionsMinimizer.reset();

    const status = document.createElement('div');
    status.className = 'insight-flow-loading-status';
    status.setAttribute('role', 'status');

    const spinner = document.createElement('span');
    spinner.className = 'insight-flow-spinner';
    spinner.setAttribute('aria-hidden', 'true');

    const label = document.createElement('span');
    label.className = 'insight-flow-loading-text';
    label.textContent = message;

    status.append(spinner, label);
    sidebar.append(status);

    const skeleton = document.createElement('div');
    skeleton.className = 'insight-flow-skeleton';
    skeleton.setAttribute('aria-hidden', 'true');

    for (let index = 0; index < 3; index += 1) {
      const card = document.createElement('div');
      card.className = 'insight-flow-skeleton-card';

      const titleLine = document.createElement('div');
      titleLine.className = 'insight-flow-skeleton-line title';

      const line = document.createElement('div');
      line.className = 'insight-flow-skeleton-line';

      const shortLine = document.createElement('div');
      shortLine.className = 'insight-flow-skeleton-line short';

      card.append(titleLine, line, shortLine);
      skeleton.append(card);
    }

    sidebar.append(skeleton);
  }

  function renderQuestions(sidebar, questions) {
    sidebar.classList.add('is-active');
    sidebar.textContent = '';

    if (questionsMinimizer) questionsMinimizer.reset();

    const hasQuestions = questions.length > 0;

    const title = document.createElement('div');
    title.className = 'question-title';

    const titleText = document.createElement('span');
    titleText.className = 'question-title-text';
    titleText.textContent = hasQuestions ? messages.questions : messages.noQuestionsGenerated;
    title.append(titleText);

    // 「卷起为圆点」按钮：button 已被拖拽逻辑排除，标题栏其余区域仍是拖拽手柄。
    if (hasQuestions && questionsMinimizer) {
      const minimizeButton = document.createElement('button');
      minimizeButton.type = 'button';
      minimizeButton.className = 'question-minimize';
      minimizeButton.title = messages.collapseQuestions;
      minimizeButton.setAttribute('aria-label', messages.collapseQuestions);

      const bar = document.createElement('span');
      bar.className = 'question-minimize-bar';
      bar.setAttribute('aria-hidden', 'true');
      minimizeButton.append(bar);

      minimizeButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        questionsMinimizer.minimize(questions.length);
      });
      title.append(minimizeButton);
    }

    sidebar.append(title);

    for (const item of questions) {
      const card = document.createElement('div');
      card.className = 'question-card';
      card.textContent = formatQuestionCardText(item);
      setupQuestionCardCopy(card, item);
      sidebar.append(card);
    }
  }

  function createQuestionDot() {
    const dot = document.createElement('div');
    dot.id = 'question-dot';
    dot.classList.add('is-hidden');
    dot.setAttribute('role', 'button');
    dot.setAttribute('tabindex', '0');
    dot.setAttribute('aria-label', messages.expandQuestions);
    dot.title = messages.expandQuestions;

    const face = document.createElement('span');
    face.className = 'question-dot-face';
    face.setAttribute('aria-hidden', 'true');
    face.textContent = '?';

    const badge = document.createElement('span');
    badge.className = 'question-dot-badge';

    dot.append(face, badge);
    return dot;
  }

  function createQuestionsMinimizer(sidebar, dot) {
    const DOT_SIZE = 40;
    const badge = dot.querySelector('.question-dot-badge');
    let minimized = false;

    // 卷起：把圆点对齐到面板的右上角，再把面板缩成圆点。
    const positionDotAtPanel = () => {
      const rect = sidebar.getBoundingClientRect();
      dot.style.top = `${Math.max(8, rect.top)}px`;
      dot.style.left = `${Math.max(8, rect.right - DOT_SIZE)}px`;
      dot.style.right = 'auto';
    };

    // 展开：把面板的右边缘对齐到圆点当前位置（圆点可被拖到任意处），并夹在视口内。
    const positionPanelAtDot = () => {
      const rect = dot.getBoundingClientRect();
      const margin = 8;
      const width = sidebar.offsetWidth || 320;
      const height = sidebar.offsetHeight || 240;
      const maxRightOffset = Math.max(margin, window.innerWidth - width - margin);
      const maxTop = Math.max(margin, window.innerHeight - height - margin);
      const rightOffset = Math.min(Math.max(window.innerWidth - rect.right, margin), maxRightOffset);
      const top = Math.min(Math.max(rect.top, margin), maxTop);
      sidebar.style.right = `${rightOffset}px`;
      sidebar.style.left = 'auto';
      sidebar.style.top = `${top}px`;
    };

    const minimize = (count) => {
      if (minimized) return;
      minimized = true;
      const n = Number(count) || 0;
      badge.textContent = n > 99 ? '99+' : String(n);
      badge.style.display = n > 0 ? 'flex' : 'none';
      positionDotAtPanel();
      sidebar.classList.add('is-min');
      dot.classList.remove('is-hidden');
    };

    const expand = () => {
      if (!minimized) return;
      minimized = false;
      positionPanelAtDot();
      sidebar.classList.remove('is-min');
      dot.classList.add('is-hidden');
    };

    const reset = () => {
      minimized = false;
      sidebar.classList.remove('is-min');
      dot.classList.add('is-hidden');
    };

    const cleanupDotDragging = setupDotDragging(dot, expand);

    return { minimize, expand, reset, cleanup: cleanupDotDragging };
  }

  // 圆点可拖动 + 点击展开：移动超过阈值算拖动，否则松手算点击（展开）。
  function setupDotDragging(dot, onTap) {
    const state = { down: false, dragging: false, pointerId: null, startX: 0, startY: 0, offsetX: 0, offsetY: 0 };
    const THRESHOLD = 5;

    const detach = () => {
      document.removeEventListener('pointermove', onPointerMove, true);
      document.removeEventListener('pointerup', onPointerUp, true);
      document.removeEventListener('pointercancel', onPointerUp, true);
    };

    const onPointerMove = (event) => {
      if (!state.down || event.pointerId !== state.pointerId) return;
      const dx = event.clientX - state.startX;
      const dy = event.clientY - state.startY;
      if (!state.dragging && Math.hypot(dx, dy) < THRESHOLD) return;
      state.dragging = true;
      dot.classList.add('is-dragging');
      const next = clampSidebarPosition(dot, event.clientX - state.offsetX, event.clientY - state.offsetY);
      dot.style.left = `${next.left}px`;
      dot.style.top = `${next.top}px`;
      dot.style.right = 'auto';
      event.preventDefault();
    };

    const onPointerUp = (event) => {
      if (event.pointerId !== state.pointerId) return;
      const wasDragging = state.dragging;
      state.down = false;
      state.dragging = false;
      state.pointerId = null;
      dot.classList.remove('is-dragging');
      try {
        if (typeof dot.releasePointerCapture === 'function') dot.releasePointerCapture(event.pointerId);
      } catch {
        // Pointer capture can already be released by the browser.
      }
      detach();
      if (!wasDragging) onTap();
    };

    const onPointerDown = (event) => {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      if (dot.classList.contains('is-hidden')) return;
      const rect = dot.getBoundingClientRect();
      state.down = true;
      state.dragging = false;
      state.pointerId = event.pointerId;
      state.startX = event.clientX;
      state.startY = event.clientY;
      state.offsetX = event.clientX - rect.left;
      state.offsetY = event.clientY - rect.top;
      try {
        if (typeof dot.setPointerCapture === 'function') dot.setPointerCapture(event.pointerId);
      } catch {
        // Pointer capture is an enhancement; document listeners keep dragging working.
      }
      document.addEventListener('pointermove', onPointerMove, true);
      document.addEventListener('pointerup', onPointerUp, true);
      document.addEventListener('pointercancel', onPointerUp, true);
    };

    const onKeyDown = (event) => {
      if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
        event.preventDefault();
        onTap();
      }
    };

    dot.addEventListener('pointerdown', onPointerDown);
    dot.addEventListener('keydown', onKeyDown);

    return () => {
      detach();
      dot.removeEventListener('pointerdown', onPointerDown);
      dot.removeEventListener('keydown', onKeyDown);
    };
  }

  function setupQuestionCardCopy(card, item) {
    // Copy only the question itself, never the category-label prefix the card may show.
    const copyText = String(item?.question || '').trim() || (card.textContent || '').trim();

    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.title = messages.copyQuestion;

    let resetTimer = null;

    const showFeedback = (ok) => {
      card.classList.remove('is-copied', 'is-copy-failed');
      card.classList.add(ok ? 'is-copied' : 'is-copy-failed');
      card.setAttribute('data-copy-feedback', ok ? messages.questionCopied : messages.questionCopyFailed);

      if (resetTimer) clearTimeout(resetTimer);
      resetTimer = setTimeout(() => {
        card.classList.remove('is-copied', 'is-copy-failed');
        card.removeAttribute('data-copy-feedback');
        resetTimer = null;
      }, 1200);
    };

    const onCopy = () => {
      if (!copyText) return;
      copyTextToClipboard(copyText).then(showFeedback).catch(() => showFeedback(false));
    };

    card.addEventListener('click', onCopy);
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
        event.preventDefault();
        onCopy();
      }
    });
  }

  function copyTextToClipboard(text) {
    const value = String(text || '');
    if (!value) return Promise.resolve(false);

    const nav = window.navigator || globalThis.navigator;
    if (nav && nav.clipboard && typeof nav.clipboard.writeText === 'function' && window.isSecureContext) {
      return nav.clipboard
        .writeText(value)
        .then(() => true)
        .catch(() => copyTextWithFallback(value));
    }

    return Promise.resolve(copyTextWithFallback(value));
  }

  function copyTextWithFallback(value) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = value;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.top = '0';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);

      const selection = document.getSelection();
      const previousRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

      textarea.focus();
      textarea.select();
      const ok = document.execCommand('copy');
      textarea.remove();

      if (previousRange && selection) {
        selection.removeAllRanges();
        selection.addRange(previousRange);
      }

      return ok;
    } catch {
      return false;
    }
  }

  function formatQuestionCardText(item) {
    const question = String(item?.question || '').trim();
    const label = String(item?.label || '').trim();

    if (!isVisibleQuestionLabel(label)) {
      return question;
    }

    return `${label}: ${question}`;
  }

  function isVisibleQuestionLabel(label) {
    const normalized = String(label || '').trim().toLowerCase();
    const hiddenFallbackLabels = new Set([
      'uncategorized',
      'unlabelled',
      'unlabeled',
      'undefined',
      'null',
      'none',
      '其他',
      '其它',
      '未分类',
    ]);

    return Boolean(normalized) && !hiddenFallbackLabels.has(normalized);
  }

  function createActionIcon() {
    const icon = document.createElement('span');
    icon.className = 'insight-flow-action-icon';
    icon.setAttribute('aria-hidden', 'true');
    return icon;
  }

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

  function createMessages() {
    return {
      immersiveReadingLabel: getI18nMessage('immersiveReadingLabel', 'Immersive reading'),
      generateQuestions: getI18nMessage('generateQuestionsTooltip', 'Generate Questions'),
      exitReadingMode: getI18nMessage('exitReadingModeTooltip', 'Exit Reading Mode'),
      autoEnterToggle: getI18nMessage('autoEnterToggleLabel', 'Auto-enter (global)'),
      autoEnterToggleTooltip: getI18nMessage(
        'autoEnterToggleTooltip',
        'Toggle auto-entering deep reading on page load (global)',
      ),
      questions: getI18nMessage('questionsLabel', 'Questions'),
      collapseQuestions: getI18nMessage('collapseQuestionsTooltip', 'Minimize to a dot'),
      expandQuestions: getI18nMessage('expandQuestionsTooltip', 'Expand questions'),
      copyQuestion: getI18nMessage('copyQuestionTooltip', 'Click to copy'),
      questionCopied: getI18nMessage('questionCopied', 'Copied'),
      questionCopyFailed: getI18nMessage('questionCopyFailed', 'Copy failed'),
      noQuestionsGenerated: getI18nMessage('noQuestionsGenerated', 'No questions generated'),
      generatingQuestions: getI18nMessage('generatingQuestions', 'Generating questions...'),
      failedToGenerateQuestions: getI18nMessage('failedToGenerateQuestions', 'Failed to generate questions'),
      extensionMessagingUnavailable: getI18nMessage(
        'extensionMessagingUnavailable',
        'Extension messaging is unavailable',
      ),
      pageContentTooShort: getI18nMessage(
        'pageContentTooShort',
        `Page content is shorter than ${minContentLength} characters`,
        [String(minContentLength)],
      ),
    };
  }

  function getI18nMessage(key, fallback, substitutions) {
    try {
      const i18n =
        (window.chrome && window.chrome.i18n) ||
        (globalThis.chrome && globalThis.chrome.i18n);
      if (!i18n || typeof i18n.getMessage !== 'function') {
        return fallback;
      }

      const message = i18n.getMessage(key, substitutions);
      return message || fallback;
    } catch {
      return fallback;
    }
  }

  function removeExistingSession() {
    if (readingWindow.__insightFlowReadingSessionCleanup) {
      readingWindow.__insightFlowReadingSessionCleanup();
      return;
    }

    document.getElementById('immersive-reading-style')?.remove();
    document.getElementById('immersive-container')?.remove();
  }
}

module.exports = { startReadingSession };
