/**
 * ContentExtractor unit test suite.
 * Run: node tests/extractor/run_tests.js
 */
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadFixture(name) {
  const filePath = path.join(__dirname, 'fixtures', name);
  return fs.readFileSync(filePath, 'utf-8');
}

function getDom(html) {
  return new JSDOM(html);
}

// ---------------------------------------------------------------------------
// Test Runner
// ---------------------------------------------------------------------------

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ ${message}`);
  }
}

function describe(name, fn) {
  console.log(`\n${name}`);
  fn();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

const { ContentExtractor } = require('../../src/extension/extractor/ContentExtractor.cjs');

describe('Test 1: Blog article extraction', () => {
  const html = loadFixture('blog.html');
  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  assert(result.content.length > 200, 'Content should be longer than 200 chars');
  assert(result.method === 'selector', `Method should be 'selector', got '${result.method}'`);
  assert(result.content.includes('Async/Await'), 'Content should contain the article title');
  assert(result.content.includes('callback hell'), 'Content should contain article body text');
  assert(!result.content.includes('50% off'), 'Content should NOT contain ad text');
  assert(!result.content.includes('推荐阅读'), 'Content should NOT contain sidebar recommendations');
  assert(!result.content.includes('Privacy'), 'Content should NOT contain footer links');
});

describe('Test 2: Tech documentation extraction', () => {
  const html = loadFixture('tech-doc.html');
  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  assert(result.content.length > 200, 'Content should be longer than 200 chars');
  assert(result.method === 'selector', `Method should be 'selector', got '${result.method}'`);
  assert(result.content.includes('Array.prototype.map'), 'Content should contain the function name');
  assert(result.content.includes('callbackFn'), 'Content should contain parameter docs');
  assert(!result.content.includes('MDN Web Docs'), 'Content should NOT contain header brand text');
});

describe('Test 3: Zhihu Chinese platform extraction', () => {
  const html = loadFixture('zhihu.html');
  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  assert(result.content.length > 300, 'Content should be substantial in length');
  assert(['selector', 'heuristic'].includes(result.method),
    `Method should be selector or heuristic, got '${result.method}'`);
  assert(result.content.includes('深度学习'), 'Content should contain the topic text');
  assert(result.content.includes('BERT'), 'Content should contain technical terms');
  assert(!result.content.includes('广告'), 'Content should NOT contain ad banners');
  assert(!result.content.includes('AI课程'), 'Content should NOT contain ad course text');
});

describe('Test 4: Heuristic fallback', () => {
  // A page with no standard semantic tags
  const html = `<!DOCTYPE html><html><body>
    <div class="custom-header">Site Logo</div>
    <div class="custom-layout">
      <div class="sidebar-nav">Menu Item 1</div>
      <div class="rich-text-content">
        <h1>The Real Article Title</h1>
        <p>This is the main article content with lots of valuable information
        about a fascinating topic that readers will enjoy learning about.</p>
        <p>Additional paragraphs provide more depth on the subject matter.</p>
      </div>
    </div>
    <div class="custom-footer">&copy; 2026</div>
  </body></html>`;

  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  assert(result.content.length > 50, 'Content should have meaningful length');
  assert(result.method === 'heuristic',
    `Method should be 'heuristic' when no semantic tag matches, got '${result.method}'`);
  assert(result.content.includes('The Real Article Title'),
    'Content should contain the article title');
});

describe('Test 5: Empty page handling', () => {
  const html = loadFixture('empty.html');
  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  assert(result.method === 'none' || result.content.length < 100,
    `Short page should return 'none' or very short content, got method='${result.method}'`);
  if (result.method === 'none') {
    assert(result.error && result.error.length > 0,
      'Error message should be present when method is none');
  }
});

describe('Test 6: Noise exclusion', () => {
  const html = loadFixture('blog.html');
  const dom = getDom(html);
  const result = ContentExtractor.extractFromDOM(dom.window.document);

  const noiseTerms = ['导航', '广告', 'Buy our', '50% off', '推荐', 'Privacy', 'Terms', 'All rights'];
  noiseTerms.forEach(term => {
    assert(!result.content.includes(term),
      `Content should NOT contain noise term: "${term}"`);
  });
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log('All tests passed! 🎉');
}
