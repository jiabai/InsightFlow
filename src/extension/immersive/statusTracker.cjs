/**
 * StatusTracker — manages two-layer status for the immersive reader pipeline.
 *
 * Domain layer (persisted / API):
 *   Pending → Processing → Completed / Failed
 *
 * Pipeline layer (UI progress, sub-states of Processing):
 *   idle → extracting → uploading → generating → done | failed | empty
 */

const STATES = {
  IDLE: 'idle',
  EXTRACTING: 'extracting',
  UPLOADING: 'uploading',
  GENERATING: 'generating',
  DONE: 'done',
  FAILED: 'failed',
  EMPTY: 'empty',
};

/** Domain-level status mapping from pipeline state */
const PIPELINE_TO_DOMAIN = {
  [STATES.IDLE]: 'Pending',
  [STATES.EXTRACTING]: 'Processing',
  [STATES.UPLOADING]: 'Processing',
  [STATES.GENERATING]: 'Processing',
  [STATES.DONE]: 'Completed',
  [STATES.FAILED]: 'Failed',
  [STATES.EMPTY]: 'Failed',
};

const STATE_MESSAGES = {
  [STATES.IDLE]: '',
  [STATES.EXTRACTING]: '正在提取页面内容...',
  [STATES.UPLOADING]: '正在上传内容...',
  [STATES.GENERATING]: '正在生成问题...',
  [STATES.DONE]: '',
  [STATES.FAILED]: '处理失败，请重试',
  [STATES.EMPTY]: '未检测到可提取的内容',
};

class StatusTracker {
  constructor() {
    this._state = STATES.IDLE;
    this._error = null;
    this._progress = 0;
  }

  /** Transition to a new pipeline state */
  setState(state, error = null) {
    if (!STATES[state.toUpperCase()]) {
      this._state = STATES.FAILED;
      this._error = `Invalid state: ${state}`;
      return;
    }
    this._state = state;
    this._error = error;
  }

  get state() { return this._state; }
  /** Domain-level status derived from pipeline state */
  get domainStatus() { return PIPELINE_TO_DOMAIN[this._state] || 'Pending'; }
  get message() { return STATE_MESSAGES[this._state] || ''; }
  get error() { return this._error; }
  get progress() { return this._progress; }
  get isLoading() { return [STATES.EXTRACTING, STATES.UPLOADING, STATES.GENERATING].includes(this._state); }
  get isFailed() { return this._state === STATES.FAILED; }
  get isEmpty() { return this._state === STATES.EMPTY; }
  get isDone() { return this._state === STATES.DONE; }

  /** Advance to next loading phase */
  startExtracting() { this.setState(STATES.EXTRACTING); this._progress = 10; }
  startUploading() { this.setState(STATES.UPLOADING); this._progress = 30; }
  startGenerating() { this.setState(STATES.GENERATING); this._progress = 60; }
  markDone() { this.setState(STATES.DONE); this._progress = 100; }
  markFailed(error) { this.setState(STATES.FAILED, error); }
  markEmpty(reason) { this.setState(STATES.EMPTY, reason); }
  reset() { this._state = STATES.IDLE; this._error = null; this._progress = 0; }
}

if (typeof module !== 'undefined') {
  module.exports = { StatusTracker, STATES, PIPELINE_TO_DOMAIN };
}
