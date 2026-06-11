# 11 - Direct Action Reading Session Entry
Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to fix

Clicking the browser extension icon should start a Reading Session directly on the active page. The current WXT manifest routes the action to a popup, so Chrome opens the popup and never calls the immersive reader engine on the page.

## Acceptance criteria

- [ ] Built Chrome manifest has a background service worker.
- [ ] Built action has no `default_popup`.
- [ ] Action click extracts readable Content from the active tab.
- [ ] Action click injects a full-screen immersive reading overlay into the active tab.
- [ ] Unsupported pages fail with a clear notification instead of silently doing nothing.

## Comments

- Root cause found on 2026-06-11: `wxt.config.ts` declares `action.default_popup`, and `src/extension/entrypoints/` has no background/content-script action path. `immersiveReader.ts` exports `enableImmersiveMode` but nothing imports or calls it.
- Fixed on 2026-06-11: Chrome builds now skip the popup entrypoint, register `background.js`, and inject the tested Reading Session renderer into the active HTTP(S) tab on action click.
