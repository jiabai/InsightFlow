/**
 * SidebarManager — manages immersive reader sidebar state.
 *
 * Pure data layer: question list, answer cache, tag grouping, progress tracking.
 * Decoupled from DOM rendering so it can be unit-tested.
 */
class SidebarManager {
  constructor() {
    /** @type {Array<{id, question, label, answered}>} */
    this._questions = [];
    /** @type {Map<number, string>} answer cache: questionId → answerText */
    this._answerCache = new Map();
    /** @type {Map<string, number>} chunkId → question index mapping */
    this._chunkIndex = new Map();
  }

  /** Load questions into the sidebar */
  loadQuestions(questions) {
    this._questions = questions.map((q, i) => ({
      ...q,
      index: i,
      answered: q.answered || false,
    }));
    this._questions.forEach((q, i) => {
      if (q.chunk_id != null) {
        this._chunkIndex.set(q.chunk_id, i);
      }
    });
  }

  /** Get questions grouped by tag */
  getTagGroups() {
    const groups = new Map();
    for (const q of this._questions) {
      const tag = q.label || 'General';
      if (!groups.has(tag)) groups.set(tag, []);
      groups.get(tag).push(q);
    }
    return Array.from(groups.entries()).map(([tag, questions]) => ({
      tag,
      questions,
      collapsed: false,
    }));
  }

  /** Mark a question as answered and cache the answer */
  setAnswer(questionId, answerText) {
    this._answerCache.set(questionId, answerText);
    const q = this._questions.find(q => q.id === questionId || q.question_id === questionId);
    if (q) q.answered = true;
  }

  /** Get cached answer or null */
  getCachedAnswer(questionId) {
    return this._answerCache.get(questionId) || null;
  }

  /** Check if question has been answered */
  isAnswered(questionId) {
    return this._answerCache.has(questionId);
  }

  /** Get question index for a given chunk_id */
  getQuestionIndexForChunk(chunkId) {
    return this._chunkIndex.get(chunkId);
  }

  /** Get all questions */
  getQuestions() {
    return this._questions;
  }

  /** Clear all state */
  reset() {
    this._questions = [];
    this._answerCache.clear();
    this._chunkIndex.clear();
  }
}

if (typeof module !== 'undefined') {
  module.exports = { SidebarManager };
}
