/**
 * StatusTracker — manages UI status states for the immersive reader pipeline.
 *
 * States: idle → extracting → uploading → generating → done | failed | empty
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
    this._progress = 0; // 0-100
  }

  /** Transition to a new state */
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
  module.exports = { StatusTracker, STATES };
}
