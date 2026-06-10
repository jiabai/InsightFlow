/**
 * SidebarManager unit tests.
 * Run: node tests/extractor/test_sidebar_manager.cjs
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

const { SidebarManager } = require('../../src/extension/immersive/sidebarManager.cjs');

function makeQuestions() {
  return [
    { id: 1, question_id: 1, question: 'What is AI?', label: 'AI', answered: false, chunk_id: 100 },
    { id: 2, question_id: 2, question: 'Why ML?', label: 'AI', answered: false, chunk_id: 200 },
    { id: 3, question_id: 3, question: 'How to code?', label: 'Programming', answered: false, chunk_id: 300 },
  ];
}

describe('Test 1: Load and group questions by tag', () => {
  const sm = new SidebarManager();
  sm.loadQuestions(makeQuestions());

  const groups = sm.getTagGroups();
  assert(groups.length === 2, `Expected 2 tag groups, got ${groups.length}`);
  assert(groups[0].tag === 'AI', 'First group should be AI');
  assert(groups[0].questions.length === 2, 'AI group should have 2 questions');
  assert(groups[1].tag === 'Programming', 'Second group should be Programming');
  assert(groups[1].questions.length === 1, 'Programming group should have 1 question');
});

describe('Test 2: Answer caching and answered state', () => {
  const sm = new SidebarManager();
  sm.loadQuestions(makeQuestions());

  assert(!sm.isAnswered(1), 'Question 1 should not be answered initially');
  assert(sm.getCachedAnswer(1) === null, 'No cached answer initially');

  sm.setAnswer(1, 'AI stands for Artificial Intelligence.');
  assert(sm.isAnswered(1), 'Question 1 should be answered after set');
  assert(sm.getCachedAnswer(1).includes('Artificial'), 'Cache should contain answer text');
});

describe('Test 3: Chunk-to-question mapping', () => {
  const sm = new SidebarManager();
  sm.loadQuestions(makeQuestions());

  assert(sm.getQuestionIndexForChunk(100) === 0, 'Chunk 100 maps to question index 0');
  assert(sm.getQuestionIndexForChunk(200) === 1, 'Chunk 200 maps to question index 1');
  assert(sm.getQuestionIndexForChunk(999) === undefined, 'Unknown chunk returns undefined');
});

describe('Test 4: Reset clears all state', () => {
  const sm = new SidebarManager();
  sm.loadQuestions(makeQuestions());
  sm.setAnswer(1, 'Answer');

  sm.reset();
  assert(sm.getQuestions().length === 0, 'Questions should be empty after reset');
  assert(!sm.isAnswered(1), 'Cache should be cleared after reset');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
