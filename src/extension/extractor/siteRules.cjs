/**
 * Site-specific extraction rules ported from Clearly-Reader.
 *
 * The rules are intentionally data-only so they can be passed through
 * chrome.scripting.executeScript({ args }) into the page context.
 */

const SITE_RULES = {
  'nytimes.com/': {
    authorName: ['.last-byline'],
    ignoreElements: ['[data-testid=photoviewer-overlay]'],
  },
  'medium.com/': {
    authorName: ['.pw-author a'],
    contentElem: 'section',
  },
  'tumblr.com/': {
    authorName: ['/"author":"(.*?)"/'],
  },
  'zhuanlan.zhuanlan.zhihu.com/': {
    authorName: ['.AuthorInfo-content .UserLink-link'],
  },
  'zhihu.com/question/': {
    contentType: 'qa',
    contentElem: '.QuestionPage',
    extractElems: ['.QuestionRichText', '.RichContent-inner'],
    extractElemsJoiner: '<hr>',
  },
  'jianshu.com/': {
    contentElem: 'section article',
    authorName: ['section span a'],
  },
  'csdn.net/': {
    contentElem: 'article',
    authorName: ['.follow-nickName'],
  },
  'techcrunch.com/': {
    authorName: ['.article__byline a'],
    contentElem: '.article-content',
  },
  'digitaltrends.com/': {
    authorName: ['a.author'],
  },
  'theverge.com/': {
    authorName: ['.c-byline__author-name'],
    contentElem: '.duet--article--article-body-component-container',
  },
  'nbcnews.com/': {
    authorName: ['.byline-name a'],
  },
  'huffpost.com/': {
    authorName: ['.entry-wirepartner__byline'],
  },
  'reuters.com/': {
    authorName: ['[rel=author]'],
  },
  'cnn.com/': {
    authorName: ['.metadata__byline__author a'],
  },
  'foxnews.com/': {
    authorName: ['.author-byline a'],
  },
  'washingtonpost.com/': {
    authorName: ['a.author-name'],
  },
  'wsj.com/': {
    authorName: ['a.author-name'],
    contentElem: '.article-content',
  },
  'abcnews.go.com/': {
    authorName: ['.Byline__Author'],
  },
  'bbc.com/': {
    authorName: ['article header strong'],
  },
  'mashable.com/': {
    contentElem: 'main article',
    authorName: ['h1 ~ div .underline-link'],
  },
  'vox.com/': {
    authorName: ['.c-byline__author-name'],
  },
  'cnet.com/': {
    authorName: ['.c-globalAuthor_link'],
  },
  'engadget.com/': {
    authorName: ['[data-component="VerticalAuthorInfo"] a[class*=engadgetSteelGray]'],
  },
  'entertainment14.net/': {
    titleElem: '.entry-title',
    contentElem: '.entry-content',
  },
  'mp.weixin.qq.com/': {
    authorName: ['.rich_media_meta_text'],
    contentElem: '.rich_media_content',
  },
  'sspai.com/': {
    authorName: ['.nickname'],
    contentElem: '.content',
  },
  'woshipm.com/': {
    authorName: ['.ui-captionStrong'],
  },
  '36kr.com/': {
    authorName: ['.title-icon-item'],
  },
  'infzm.com/': {
    authorName: ['.nfzm-content__author'],
  },
  'cnbeta.com/': {
    authorName: ['.source'],
  },
  'huxiu.com/': {
    authorName: ['.author-info__username'],
  },
  'sciencedirect.com/': {
    contentElem: 'article',
  },
  'wattpad.com/': {
    contentElem: '.part-content pre',
  },
  'pcmag.com/': {
    contentElem: 'article',
  },
  'cntraveler.com/gallery': {
    contentElem: '[data-attribute-verso-pattern="gallery-body"]',
  },
  'plato.stanford.edu/entries': {
    contentElem: '#article',
  },
  'utgd.net/': {
    contentElem: '.content-inner',
  },
  'wikipedia.org/wiki/': {
    contentElem: '#mw-content-text',
  },
  'officesnapshots.com/': {
    contentElem: '.post',
    excludeElems: ['.photo-sidebar', '.signup-modal-button', '.tooltip-garage'],
  },
  'yuque.com/': {
    contentElem: '.ne-viewer-body',
    excludeElems: ['.ne-ui-image-ocr-mask', '.ne-ui-image-inner-button-wrap'],
  },
  'lifehacker.com/': {
    contentElem: '.js_post-content',
    excludeElems: [
      '.js_related-stories-inset',
      '.instream-native-video',
      '#sidebar_wrapper',
      '.js_ad-dynamic',
      '.js_commerce-inset-permalink',
      '.ad-unit',
      '.ad-mobile',
    ],
  },
  'lifewire.com/': {
    contentElem: '.structured-content',
  },
  'mondiplo.com/': {
    contentElem: '#content',
  },
  'stackoverflow.com/questions/': {
    contentType: 'qa',
    contentElem: '#mainbar',
    extractElems: ['.js-post-body'],
    extractElemsJoiner: '<hr>',
  },
  'segmentfault.com/q/': {
    contentType: 'qa',
    contentElem: '#questionMain',
    extractElems: ['.article-content'],
    extractElemsJoiner: '<hr>',
  },
  'github.com/*/*/issues/': {
    contentType: 'discussion',
    contentElem: '.Layout-main',
    extractElems: ['.comment-body'],
    extractElemsJoiner: '<hr>',
  },
  'github.com/*/*/discussions/': {
    contentType: 'discussion',
    contentElem: '.discussion',
    extractElems: ['.comment-body'],
    extractElemsJoiner: '<hr>',
  },
  'github.com/*/*/wiki': {
    contentElem: '.Layout-main',
  },
  'reddit.com/r/*/comments': {
    contentType: 'discussion',
    contentElem: 'div[tabindex="0"] + div',
    extractElems: ['.RichTextJSON-root', '[testid="comment"]'],
    extractElemsJoiner: '<hr>',
  },
  'developer.aliyun.com/article/': {
    contentElem: '.article-inner',
  },
  'cloud.tencent.com/developer/article/': {
    contentElem: '.J-articleContent',
  },
  'www.youtube.com/': {
    readable: false,
  },
  'accounts.google.com/': {
    readable: false,
  },
  'myaccount.google.com/': {
    readable: false,
  },
  'translate.google.com/': {
    readable: false,
  },
  'mail.google.com/': {
    readable: false,
  },
  'drive.google.com/': {
    readable: false,
  },
  'docs.google.com/': {
    readable: false,
  },
  'spreadsheet.google.com/': {
    readable: false,
  },
};

function getSiteRule(url, siteRules = SITE_RULES) {
  const sourceUrl = String(url || '');
  const key = Object.keys(siteRules || {}).find((pattern) => urlMatchesRule(sourceUrl, pattern));
  return key ? siteRules[key] : undefined;
}

function isReadableUrl(url, siteRules = SITE_RULES) {
  const rule = getSiteRule(url, siteRules);
  return !rule || rule.readable !== false;
}

function urlMatchesRule(url, pattern) {
  if (!url || !pattern) return false;
  if (pattern.includes('*')) {
    return wildcardPatternToRegExp(pattern).test(url);
  }
  return url.includes(pattern);
}

function wildcardPatternToRegExp(pattern) {
  const escapedParts = pattern.split('*').map(escapeRegExp);
  return new RegExp(escapedParts.join('.*?'));
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

module.exports = {
  SITE_RULES,
  getSiteRule,
  isReadableUrl,
  urlMatchesRule,
};
