const assert = require('assert');
const { JSDOM } = require('jsdom');
const { startReadingSession } = require('../../src/extension/immersive/readingSession.cjs');

const previousWindow = global.window;
const previousDocument = global.document;
const previousChrome = global.chrome;

const articleText = Array(80)
  .fill('This paragraph represents a WeChat article body with enough useful reading content.')
  .join(' ');

const dom = new JSDOM(
  `<!doctype html>
  <html>
    <head><title>Fallback Title</title></head>
    <body>
      <h1 id="activity-name">WeChat Article Title</h1>
      <div id="js_content" class="rich_media_content">
        <p id="source-paragraph" class="source-layout-card" data-track="source-css">${articleText}</p>
        <img
          src="data:image/gif;base64,R0lGODlhAQABAAAAACw="
          data-src="https://mmbiz.qpic.cn/mmbiz_png/example/640?wx_fmt=png&amp;from=appmsg"
          data-original="https://should-not-win.example/original.png"
          alt="WeChat lazy image"
        />
        <script>window.__bad = true;</script>
      </div>
    </body>
  </html>`,
  { url: 'https://mp.weixin.qq.com/s/example', pretendToBeVisual: true },
);

global.window = dom.window;
global.document = dom.window.document;
global.chrome = {
  runtime: {
    sendMessage(message, callback) {
      assert.strictEqual(message.type, 'INSIGHTFLOW_GENERATE_QUESTIONS');
      assert(message.content.includes('WeChat article body'), 'Generate Questions should send extracted Content');
      callback({
        ok: true,
        questions: [
          {
            question: 'What is the central idea?',
            label: 'Comprehension',
            question_id: 1,
            chunk_id: 1,
          },
        ],
      });
    },
  },
};
global.window.chrome = global.chrome;

(async () => {
try {
  const result = startReadingSession();

  assert.strictEqual(result.ok, true, result.error);
  assert(result.length > 500, 'Reading Session should extract substantial Content');
  assert.strictEqual(result.method, 'selector');

  const container = document.getElementById('immersive-container');
  assert(container, 'Reading Session should render an immersive container');
  assert(document.getElementById('insight-flow-header'), 'Reading Session should render the InsightFlow header');
  assert(document.getElementById('insight-flow-header').textContent.includes('InsightFlow'));
  assert(document.getElementById('immersive-content-area'), 'Reading Session should render the content area');
  assert(
    document.querySelector('#immersive-content-area article.insight-flow-article'),
    'Reading Session should wrap extracted content in an article element',
  );
  assert(document.getElementById('question-sidebar'), 'Reading Session should reserve the question sidebar');
  assert(document.getElementById('generate-questions'), 'Reading Session should render the generate questions button');
  assert.strictEqual(document.getElementById('generate-questions').dataset.tooltip, 'Generate Questions');
  assert.strictEqual(document.getElementById('immersive-close').dataset.tooltip, 'Exit Reading Mode');
  assert(
    document.querySelector('#generate-questions .insight-flow-action-icon[aria-hidden="true"]'),
    'Generate Questions should render a dedicated geometric icon element',
  );
  assert(
    document.querySelector('#immersive-close .insight-flow-action-icon[aria-hidden="true"]'),
    'Exit Reading Mode should render a dedicated geometric icon element',
  );
  assert.strictEqual(document.getElementById('generate-questions').textContent, '');
  assert.strictEqual(document.getElementById('immersive-close').textContent, '');
  assert(!container.innerHTML.includes('<script>'), 'Reading Session should remove scripts from extracted Content');
  assert(
    !document.querySelector('#immersive-content-area .source-layout-card'),
    'Reading Session should strip source page classes from extracted Content',
  );
  assert(
    !document.querySelector('#immersive-content-area #source-paragraph'),
    'Reading Session should strip source page ids from extracted Content',
  );
  assert(
    !document.getElementById('immersive-content-area').innerHTML.includes('data-track='),
    'Reading Session should strip source page data attributes from extracted Content',
  );
  const readingStyle = document.getElementById('immersive-reading-style').textContent;
  assert(readingStyle.includes('background: #303030'));
  assert(readingStyle.includes('background: #050505'));
  assert(
    readingStyle.includes('width: min(1700px, calc(100vw - 160px))'),
    'Reading Session should use a wide Clearly Reader-style desktop measure',
  );
  assert(readingStyle.includes('max-width: none'), 'Reading Session content should not force a narrow column');
  assert(readingStyle.includes('border-radius: 12px'), 'Reading Session should keep a softly rounded content panel');
  assert(readingStyle.includes('top: 22px'), 'Reading Session action buttons should be inset from the top edge');
  assert(readingStyle.includes('right: 22px'), 'Reading Session action buttons should be inset from the right edge');
  assert(readingStyle.includes('width: 52px'), 'Reading Session action buttons should avoid oversized controls');
  assert(readingStyle.includes('padding: 0'), 'Reading Session action buttons should reset source/default padding');
  assert(readingStyle.includes('appearance: none'), 'Reading Session action buttons should reset native appearance');
  assert(
    readingStyle.includes('translate(-50%, -50%)'),
    'Reading Session action icons should be geometrically centered',
  );
  assert(
    readingStyle.includes('rotate(90deg)') && readingStyle.includes('rotate(45deg)'),
    'Reading Session action icons should use CSS-drawn plus and close marks',
  );
  assert(
    readingStyle.includes('box-shadow: 0 18px 40px rgba(0, 0, 0, 0.38)'),
    'Reading Session should keep the content panel visually lifted from the background',
  );
  assert(readingStyle.includes('padding: 30px 96px 80px'), 'Reading Session should use wide content padding');
  assert(
    readingStyle.includes('font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"'),
    'Reading Session body font should follow the system font stack',
  );
  assert(readingStyle.includes('line-height: 1.66em'), 'Reading Session should use Clearly Reader content line height');
  assert(readingStyle.includes('letter-spacing: 0em'), 'Reading Session should keep Clearly Reader letter spacing');
  assert(readingStyle.includes('font-size: 22px'), 'Reading Session should use Clearly Reader body text scale');
  assert(readingStyle.includes('margin-top: 1.24em'), 'Reading Session should use Clearly Reader paragraph rhythm');
  const renderedImage = document.querySelector('#immersive-content-area img[alt="WeChat lazy image"]');
  assert(renderedImage, 'Reading Session should preserve WeChat article images');
  assert.strictEqual(
    renderedImage.getAttribute('src'),
    'https://mmbiz.qpic.cn/mmbiz_png/example/640?wx_fmt=png&from=appmsg',
    'Reading Session should replace WeChat placeholder image src with data-src',
  );
  assert.strictEqual(document.body.style.overflow, 'hidden');

  document.getElementById('generate-questions').click();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert(document.getElementById('question-sidebar').textContent.includes('What is the central idea?'));

  document.getElementById('immersive-close').click();
  assert.strictEqual(document.getElementById('immersive-container'), null);
  assert.strictEqual(document.body.style.overflow, '');

  console.log('Reading Session DOM checks passed');
} finally {
  global.window = previousWindow;
  global.document = previousDocument;
  global.chrome = previousChrome;
}
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
