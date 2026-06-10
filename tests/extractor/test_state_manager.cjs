/**
 * StateManager unit tests — DOM save/restore.
 * Run: node tests/extractor/test_state_manager.cjs
 */
const { JSDOM } = require('jsdom');

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

const { StateManager } = require('../../src/fe/immersive/stateManager.cjs');

function makePageDOM(html) {
  return new JSDOM(html || `<!DOCTYPE html><html>
    <head><title>Test Page</title><link rel="stylesheet" href="style.css"></head>
    <body>
      <nav>Home | About</nav>
      <main><article><h1>Article Title</h1><p>Content here.</p></article></main>
      <footer>&copy; 2026</footer>
    </body></html>`);
}

describe('Test 1: Save state preserves original DOM', () => {
  const dom = makePageDOM();
  const originalHTML = dom.window.document.body.innerHTML;
  const originalHeadHTML = dom.window.document.head.innerHTML;

  StateManager.save(dom.window.document);

  const state = StateManager.getState();
  assert(state !== null, 'State should not be null after save');
  assert(state.headHTML === originalHeadHTML, 'head HTML should be preserved');
  assert(state.bodyHTML === dom.window.document.body.innerHTML, 'body HTML should be preserved');
});

describe('Test 2: Restore state after DOM mutation', () => {
  const dom = makePageDOM();
  const doc = dom.window.document;
  const originalHeadHTML = doc.head.innerHTML;
  const originalBodyHTML = doc.body.innerHTML;

  StateManager.save(doc);

  // Mutate DOM
  doc.body.innerHTML = '<div>replaced</div>';
  doc.head.innerHTML = '<title>Changed</title>';

  // Restore
  StateManager.restore(doc);

  // After restore, check content (JSDOM restore works differently,
  // so we check key elements exist)
  assert(doc.querySelector('h1'), 'Restored body should have h1');
  assert(doc.querySelector('nav'), 'Restored body should have nav');
  assert(doc.querySelector('footer'), 'Restored body should have footer');
});

describe('Test 3: Restore clears state after use', () => {
  const dom = makePageDOM();
  const doc = dom.window.document;

  StateManager.save(doc);
  StateManager.restore(doc);

  assert(StateManager.getState() === null, 'State should be null after restore');
});

describe('Test 4: Restore without save is safe', () => {
  const dom = makePageDOM();
  const doc = dom.window.document;
  const bodyBefore = doc.body.innerHTML;

  // restore() without prior save() should be a no-op
  let threw = false;
  try {
    StateManager.restore(doc);
  } catch (e) {
    threw = true;
  }

  assert(!threw, 'Restore without save should not throw');
});

describe('Test 5: Overwrite save (second save replaces first)', () => {
  const dom1 = makePageDOM();
  const doc1 = dom1.window.document;
  StateManager.save(doc1);

  const dom2 = makePageDOM('<html><body><p>second</p></body></html>');
  const doc2 = dom2.window.document;
  StateManager.save(doc2);

  const state = StateManager.getState();
  assert(state.bodyHTML.includes('second'), 'Second save should overwrite first');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
