/**
 * MarkdownRenderer unit tests.
 * Run: node tests/extractor/test_markdown_renderer.cjs
 */
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Test Runner
// ---------------------------------------------------------------------------

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) { passed++; console.log(`  ✓ ${message}`); }
  else { failed++; console.error(`  ✗ ${message}`); }
}

function describe(name, fn) {
  console.log(`\n${name}`);
  fn();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

const { MarkdownRenderer } = require('../../src/fe/immersive/markdownRenderer.cjs');

describe('Test 1: Basic Markdown rendering', () => {
  const md = '# Heading\n\n**bold** and *italic*\n\n- item 1\n- item 2';
  const html = MarkdownRenderer.render(md);

  assert(html.includes('<h1'), 'Should render h1 heading');
  assert(html.includes('Heading'), 'Should contain heading text');
  assert(html.includes('<strong>bold</strong>'), 'Should render bold text');
  assert(html.includes('<em>italic</em>'), 'Should render italic text');
  assert(html.includes('<li>item 1</li>'), 'Should render list items');
});

describe('Test 2: Empty content handling', () => {
  const result = MarkdownRenderer.render('');
  assert(result === '' || result.error,
    'Empty input should return empty string or error');
});

describe('Test 3: Full document rendering', () => {
  const md = fs.readFileSync(
    path.join(__dirname, 'fixtures', 'immersive-input.md'), 'utf-8'
  );
  const html = MarkdownRenderer.render(md);

  assert(html.length > md.length, 'HTML should be longer than markdown input');
  assert(html.includes('<h1>'), 'Should have h1');
  assert(html.includes('<h2>'), 'Should have h2');
  assert(html.includes('<h3>'), 'Should have h3');
  assert(html.includes('<code>'), 'Should have inline code');
  assert(html.includes('<pre><code'), 'Should have code blocks');
  assert(html.includes('<blockquote>'), 'Should have blockquotes');
  assert(html.includes('<ol>'), 'Should have ordered lists');
});

describe('Test 4: Render with wrapper', () => {
  const md = 'Simple text';
  const html = MarkdownRenderer.render(md, { wrap: true });

  assert(html.includes('immersive-content'), 'Wrapper should include class name');
  assert(html.includes('Simple text'), 'Content should be inside wrapper');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
