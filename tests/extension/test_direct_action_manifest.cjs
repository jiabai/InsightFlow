const assert = require('assert');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const extensionDir = path.join(repoRoot, 'src', 'extension');
const manifestPath = path.join(extensionDir, '.output', 'chrome-mv3', 'manifest.json');

childProcess.execSync('npm run build', {
  cwd: extensionDir,
  stdio: 'pipe',
});

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

assert(
  manifest.background && manifest.background.service_worker,
  'Chrome manifest should register a background service worker for direct action clicks',
);

assert(
  !Object.prototype.hasOwnProperty.call(manifest.action || {}, 'default_popup'),
  'Extension action should not define default_popup when icon click starts the Reading Session',
);

console.log('Direct action manifest checks passed');
