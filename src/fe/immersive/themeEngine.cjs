/**
 * ThemeEngine — generates CSS for light and dark immersive reading themes.
 */
class ThemeEngine {
  /** @param {'light'|'dark'} theme */
  static generateCSS(theme = 'light') {
    return theme === 'dark' ? DARK_THEME : LIGHT_THEME;
  }
}

const LIGHT_THEME = `
  body { margin: 0 !important; padding: 0 !important; background-color: #f8fafc !important; }
  #immersive-container {
    display: flex !important;
    position: fixed !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    overflow-y: auto !important;
    margin: 0 !important;
    z-index: 99999 !important;
  }
  #immersive-content-area {
    flex: 1;
    max-width: 800px;
    margin: 0 auto;
    padding: 3rem 2rem;
    background-color: #ffffff;
    color: #1a1a2e;
    min-height: 100%;
  }
  #immersive-content-area h1 { font-size: 2rem; color: #1e3a5f; margin-top: 2rem; margin-bottom: 1rem; }
  #immersive-content-area h2 { font-size: 1.5rem; color: #2c5282; margin-top: 1.5rem; margin-bottom: 0.75rem; }
  #immersive-content-area h3 { font-size: 1.25rem; color: #2b6cb0; }
  #immersive-content-area p { font-size: 1.1rem; line-height: 1.8; margin-bottom: 1.5rem; color: #333; }
  #immersive-content-area code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
  #immersive-content-area pre { background: #f5f5f5; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  #immersive-content-area pre code { background: none; padding: 0; }
  #immersive-content-area blockquote { border-left: 4px solid #3b82f6; padding-left: 1rem; margin-left: 0; color: #555; }
  #immersive-content-area ul, #immersive-content-area ol { padding-left: 1.5rem; }
  #immersive-content-area li { margin-bottom: 0.5rem; }
  #immersive-sidebar {
    width: 320px;
    min-width: 320px;
    background-color: #ffffff;
    border-left: 1px solid #e2e8f0;
    box-shadow: -2px 0 10px rgba(0,0,0,0.05);
    overflow-y: auto;
    padding: 2rem 1.5rem;
    z-index: 99998;
  }
  #immersive-sidebar h3 { margin-top: 0; color: #2c3e50; font-size: 1.1rem; }
  #immersive-close {
    position: fixed;
    top: 1rem; right: 340px;
    padding: 0.5rem 1rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    z-index: 100000;
    font-size: 0.9rem;
  }
  #immersive-close:hover { background: #2563eb; }
`;

const DARK_THEME = `
  body { margin: 0 !important; padding: 0 !important; background-color: #0d1117 !important; }
  #immersive-container {
    display: flex !important;
    position: fixed !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    overflow-y: auto !important;
    margin: 0 !important;
    z-index: 99999 !important;
  }
  #immersive-content-area {
    flex: 1;
    max-width: 800px;
    margin: 0 auto;
    padding: 3rem 2rem;
    background-color: #161b22;
    color: #c9d1d9;
    min-height: 100%;
  }
  #immersive-content-area h1 { font-size: 2rem; color: #58a6ff; margin-top: 2rem; margin-bottom: 1rem; }
  #immersive-content-area h2 { font-size: 1.5rem; color: #79c0ff; margin-top: 1.5rem; margin-bottom: 0.75rem; }
  #immersive-content-area h3 { font-size: 1.25rem; color: #a5d6ff; }
  #immersive-content-area p { font-size: 1.1rem; line-height: 1.8; margin-bottom: 1.5rem; color: #c9d1d9; }
  #immersive-content-area code { background: #21262d; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #ff7b72; }
  #immersive-content-area pre { background: #21262d; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  #immersive-content-area pre code { background: none; padding: 0; color: #c9d1d9; }
  #immersive-content-area blockquote { border-left: 4px solid #58a6ff; padding-left: 1rem; margin-left: 0; color: #8b949e; }
  #immersive-content-area ul, #immersive-content-area ol { padding-left: 1.5rem; }
  #immersive-content-area li { margin-bottom: 0.5rem; }
  #immersive-sidebar {
    width: 320px;
    min-width: 320px;
    background-color: #161b22;
    border-left: 1px solid #30363d;
    box-shadow: -2px 0 10px rgba(0,0,0,0.3);
    overflow-y: auto;
    padding: 2rem 1.5rem;
    z-index: 99998;
  }
  #immersive-sidebar h3 { margin-top: 0; color: #c9d1d9; font-size: 1.1rem; }
  #immersive-close {
    position: fixed;
    top: 1rem; right: 340px;
    padding: 0.5rem 1rem;
    background: #238636;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    z-index: 100000;
    font-size: 0.9rem;
  }
  #immersive-close:hover { background: #2ea043; }
`;

module.exports = { ThemeEngine };
