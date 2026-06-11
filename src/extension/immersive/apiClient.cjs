/**
 * ImmersiveAPI — wraps backend REST API calls for the immersive reader.
 *
 * Handles: upload content, poll status, fetch questions, stream answers.
 */
class ImmersiveAPI {
  /**
   * @param {string} baseUrl - Backend API base URL
   * @param {string} userId - SHA-256 user identifier
   */
  constructor(baseUrl, userId) {
    this._base = baseUrl.replace(/\/$/, '');
    this._userId = userId;
  }

  /** Upload markdown content → { file_id, ... } */
  async upload(content) {
    const formData = new FormData();
    formData.append('file', new Blob([content], { type: 'text/markdown' }), 'page.md');
    const r = await fetch(`${this._base}/upload/${this._userId}`, {
      method: 'POST', body: formData,
    });
    if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
    return r.json();
  }

  /** Get file processing status → { file_id, status } */
  async getStatus(fileId) {
    const r = await fetch(`${this._base}/file_status/${fileId}`);
    if (!r.ok) throw new Error(`Status check failed: ${r.status}`);
    return r.json();
  }

  /** Trigger question generation → 202 Accepted */
  async generateQuestions(fileId) {
    const r = await fetch(`${this._base}/questions/generate/${this._userId}/${fileId}`, {
      method: 'POST',
    });
    if (!r.ok) throw new Error(`Generate failed: ${r.status}`);
    return r.json();
  }

  /** Fetch generated questions → [{ question, label, ... }] */
  async getQuestions(fileId) {
    const r = await fetch(`${this._base}/questions/${fileId}`);
    if (!r.ok) throw new Error(`Questions fetch failed: ${r.status}`);
    return r.json();
  }

  /** Poll until status becomes "Completed" or fails */
  async waitForCompletion(fileId, { interval = 1000, timeout = 60000 } = {}) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const s = await this.getStatus(fileId);
      if (s.status === 'Completed') return s;
      if (s.status === 'Failed') throw new Error('Processing failed');
      await new Promise(r => setTimeout(r, interval));
    }
    throw new Error('Processing timed out');
  }

  /** Stream LLM answer for a question */
  async *streamAnswer(questionId, chunkId) {
    const r = await fetch(`${this._base}/llm/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, chunk_id: chunkId }),
    });
    if (!r.ok) throw new Error(`Stream failed: ${r.status}`);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ') && !line.includes('[DONE]')) {
          try {
            const chunk = JSON.parse(line.slice(6));
            const content = chunk.choices?.[0]?.delta?.content;
            if (content) yield content;
          } catch { /* skip malformed chunks */ }
        }
      }
    }
  }
}

if (typeof module !== 'undefined') {
  module.exports = { ImmersiveAPI };
}
