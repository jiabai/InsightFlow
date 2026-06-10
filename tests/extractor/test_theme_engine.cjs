/**
 * ThemeEngine unit tests.
 * Run: node tests/extractor/test_theme_engine.cjs
 */

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

const { ThemeEngine } = require('../../src/fe/immersive/themeEngine.cjs');

describe('Test 1: Light theme generates CSS', () => {
  const css = ThemeEngine.generateCSS('light');
  assert(css.length > 100, 'CSS should be substantial');
  assert(css.includes('background'), 'Should have background property');
  assert(css.includes('color'), 'Should have color property');
  assert(!css.includes('#0d'), 'Light theme should NOT have dark background hex');
});

describe('Test 2: Dark theme generates CSS', () => {
  const css = ThemeEngine.generateCSS('dark');
  assert(css.length > 100, 'CSS should be substantial');
  assert(css.includes('background'), 'Should have background property');
  assert(css.includes('color'), 'Should have color property');
  // Dark theme should have dark background
  assert(
    css.includes('#1a') || css.includes('#2d') || css.includes('#0d') || css.includes('dark'),
    'Dark theme should contain dark colors'
  );
});

describe('Test 3: Light and dark differ', () => {
  const light = ThemeEngine.generateCSS('light');
  const dark = ThemeEngine.generateCSS('dark');
  assert(light !== dark, 'Light and dark themes must be different');
});

describe('Test 4: Missing theme falls back', () => {
  const css = ThemeEngine.generateCSS('nonexistent');
  assert(css.length > 100, 'Unknown theme should fall back without error');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
