/**
 * RetryManager — exponential backoff retry logic.
 *
 * Handles transient failures (network issues, timeouts) with
 * configurable retry count and backoff strategy.
 */

class RetryManager {
  /**
   * @param {{ maxRetries?: number, baseDelay?: number, maxDelay?: number }} options
   */
  constructor(options = {}) {
    this.maxRetries = options.maxRetries || 3;
    this.baseDelay = options.baseDelay || 1000; // ms
    this.maxDelay = options.maxDelay || 10000; // ms
  }

  /**
   * Execute an async function with retry on failure.
   *
   * @param {() => Promise<any>} fn - The async function to retry
   * @param {(error: Error) => boolean} shouldRetry - Returns true if error is retryable
   * @returns {Promise<{ result: any, attempts: number, success: boolean }>}
   */
  async execute(fn, shouldRetry = () => true) {
    let lastError = null;

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        const result = await fn();
        return { result, attempts: attempt, success: true };
      } catch (error) {
        lastError = error;
        if (attempt < this.maxRetries && shouldRetry(error)) {
          const delay = Math.min(
            this.baseDelay * Math.pow(2, attempt - 1),
            this.maxDelay,
          );
          await this._sleep(delay);
        }
      }
    }

    return {
      result: null,
      attempts: this.maxRetries,
      success: false,
      error: lastError,
    };
  }

  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

if (typeof module !== 'undefined') {
  module.exports = { RetryManager };
}
