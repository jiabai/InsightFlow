/**
 * StateManager — saves and restores the original page DOM state
 * before immersive mode takes over.
 */
let _state = null;

class StateManager {
  /**
   * Save the current DOM state.
   * @param {Document} doc
   */
  static save(doc) {
    _state = {
      headHTML: doc.head.innerHTML,
      bodyHTML: doc.body.innerHTML,
    };
  }

  /**
   * Restore the original DOM state. Clears saved state after use.
   * @param {Document} doc
   */
  static restore(doc) {
    if (!_state) return;
    doc.head.innerHTML = _state.headHTML;
    doc.body.innerHTML = _state.bodyHTML;
    _state = null;
  }

  /**
   * Get the current saved state (for testing).
   * @returns {{ headHTML: string, bodyHTML: string } | null}
   */
  static getState() {
    return _state;
  }

  /**
   * Clear saved state without restoring (for testing).
   */
  static clear() {
    _state = null;
  }
}

module.exports = { StateManager };
