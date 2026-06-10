/**
 * StatusTracker & RetryManager unit tests.
 * Run: node tests/extractor/test_error_states.cjs
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

const { StatusTracker } = require('../../src/extension/immersive/statusTracker.cjs');
const { RetryManager } = require('../../src/extension/immersive/retryManager.cjs');

// -- StatusTracker --

describe('Test 1: StatusTracker state transitions', () => {
  const st = new StatusTracker();
  assert(st.state === 'idle', 'Initial state should be idle');
  assert(st.isLoading === false, 'Should not be loading initially');
  assert(st.progress === 0, 'Progress should start at 0');

  st.startExtracting();
  assert(st.state === 'extracting', 'Should be extracting');
  assert(st.isLoading === true, 'Should be loading');
  assert(st.progress === 10, 'Progress should be 10 after extracting');
  assert(st.message.includes('提取'), 'Message should mention extracting');

  st.startUploading();
  assert(st.state === 'uploading', 'Should be uploading');
  assert(st.progress === 30, 'Progress should be 30 after uploading');

  st.startGenerating();
  assert(st.state === 'generating', 'Should be generating');
  assert(st.progress === 60, 'Progress should be 60 after generating');

  st.markDone();
  assert(st.state === 'done', 'Should be done');
  assert(st.isDone === true, 'isDone should be true');
  assert(st.progress === 100, 'Progress should be 100');
});

describe('Test 2: StatusTracker error and empty states', () => {
  const st = new StatusTracker();
  st.markFailed('Network timeout');
  assert(st.isFailed === true, 'Should be failed');
  assert(st.error === 'Network timeout', 'Error message should be set');

  st.markEmpty('No content detected');
  assert(st.isEmpty === true, 'Should be empty');
});

describe('Test 3: StatusTracker reset', () => {
  const st = new StatusTracker();
  st.startGenerating();
  st.markFailed('Error');
  st.reset();
  assert(st.state === 'idle', 'After reset should be idle');
  assert(st.error === null, 'Error should be null after reset');
  assert(st.progress === 0, 'Progress should be 0 after reset');
});

// -- RetryManager --

describe('Test 4: RetryManager succeeds on first try', async () => {
  const rm = new RetryManager({ maxRetries: 3 });
  const { result, attempts, success } = await rm.execute(
    async () => 'ok',
  );
  assert(success === true, 'Should succeed');
  assert(attempts === 1, 'Should take 1 attempt');
  assert(result === 'ok', 'Should return the value');
});

describe('Test 5: RetryManager retries on failure', async () => {
  const rm = new RetryManager({ maxRetries: 3, baseDelay: 1 });
  let calls = 0;
  const { success, attempts } = await rm.execute(async () => {
    calls++;
    throw new Error('Transient error');
  });
  assert(success === false, 'Should fail after max retries');
  assert(attempts === 3, 'Should try 3 times');
  assert(calls === 3, 'Should call function 3 times');
});

describe('Test 6: RetryManager succeeds after retry', async () => {
  const rm = new RetryManager({ maxRetries: 3, baseDelay: 1 });
  let calls = 0;
  const { success, attempts, result } = await rm.execute(async () => {
    calls++;
    if (calls < 2) throw new Error('Fail');
    return 'recovered';
  });
  assert(success === true, 'Should eventually succeed');
  assert(attempts === 2, 'Should take 2 attempts');
  assert(result === 'recovered', 'Should return value');
});

describe('Test 7: RetryManager respects shouldRetry', async () => {
  const rm = new RetryManager({ maxRetries: 3, baseDelay: 1 });
  let calls = 0;
  const { attempts } = await rm.execute(
    async () => { calls++; throw new Error('Permanent error'); },
    () => false, // never retry
  );
  assert(attempts === 1, 'Should not retry when shouldRetry returns false');
  assert(calls === 1, 'Should call only once');
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${'='.repeat(50)}`);
console.log(`Passed: ${passed}, Failed: ${failed}`);
process.exit(failed > 0 ? 1 : 0);
