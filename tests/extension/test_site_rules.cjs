const assert = require('assert');
const { JSDOM } = require('jsdom');
const {
  SITE_RULES,
  getSiteRule,
  isReadableUrl,
} = require('../../src/extension/extractor/siteRules.cjs');
const { ContentExtractor } = require('../../src/extension/extractor/ContentExtractor.cjs');
const { startReadingSession } = require('../../src/extension/immersive/readingSession.cjs');

assert(
  Object.keys(SITE_RULES).length > 40,
  'Clearly-Reader site rules should include more than 40 optimized entries',
);

assert.strictEqual(
  getSiteRule('https://github.com/openai/codex/issues/123')?.contentType,
  'discussion',
  'Wildcard GitHub issue URLs should resolve to discussion extraction rules',
);

assert.strictEqual(
  isReadableUrl('https://www.youtube.com/watch?v=abc', SITE_RULES),
  false,
  'Clearly-Reader unreadable sites should remain disabled',
);

const longQuestion = Array(20)
  .fill('How should this implementation preserve the meaningful technical details from the question?')
  .join(' ');
const longAnswer = Array(20)
  .fill('The accepted answer explains the reasoning, caveats, and concrete implementation steps.')
  .join(' ');

const stackOverflowDom = new JSDOM(
  `<!doctype html>
  <html>
    <head><title>StackOverflow Extraction</title></head>
    <body>
      <div id="mainbar">
        <div class="question">
          <div class="js-post-body"><p>${longQuestion}</p></div>
        </div>
        <div class="answer">
          <div class="js-post-body"><p>${longAnswer}</p></div>
        </div>
      </div>
      <aside class="sidebar">Promoted jobs and unrelated links should not be extracted.</aside>
    </body>
  </html>`,
  { url: 'https://stackoverflow.com/questions/123/example' },
);

const extracted = ContentExtractor.extractFromDOM(stackOverflowDom.window.document);
assert.strictEqual(extracted.method, 'site-rule-qa');
assert(extracted.content.includes('meaningful technical details'), 'Question body should be extracted');
assert(extracted.content.includes('accepted answer explains'), 'Answer body should be extracted');
assert(!extracted.content.includes('Promoted jobs'), 'Sidebar content should not be extracted');

const previousWindow = global.window;
const previousDocument = global.document;
const previousChrome = global.chrome;

global.window = stackOverflowDom.window;
global.document = stackOverflowDom.window.document;
global.chrome = {
  runtime: {
    sendMessage(_message, callback) {
      callback({ ok: true, questions: [] });
    },
  },
  i18n: {
    getMessage() {
      return '';
    },
  },
};
global.window.chrome = global.chrome;

try {
  const result = startReadingSession(SITE_RULES);
  assert.strictEqual(result.ok, true, result.error);
  assert.strictEqual(result.method, 'site-rule-qa');
  assert(
    document.getElementById('immersive-content-area').textContent.includes('accepted answer explains'),
    'Reading Session should render site-rule extracted discussion content',
  );
  assert(
    !document.getElementById('immersive-content-area').textContent.includes('Promoted jobs'),
    'Reading Session should omit content outside the site-rule extraction set',
  );
} finally {
  global.window = previousWindow;
  global.document = previousDocument;
  global.chrome = previousChrome;
}

console.log('Clearly-Reader site rule migration checks passed');
