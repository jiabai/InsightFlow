/**
 * MarkdownRenderer — converts Markdown to HTML for the immersive reader.
 *
 * Uses the 'marked' library for parsing.
 */
const { marked } = require('marked');

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
});

class MarkdownRenderer {
  /**
   * Render Markdown string to HTML.
   *
   * @param {string} markdown
   * @param {{ wrap?: boolean }} options
   * @returns {string} HTML string
   */
  static render(markdown, options = {}) {
    if (!markdown || markdown.trim().length === 0) {
      return '';
    }

    const body = marked.parse(markdown);

    if (options.wrap) {
      return `<div class="immersive-content">${body}</div>`;
    }

    return body;
  }
}

module.exports = { MarkdownRenderer };
