# 12 - WeChat Immersive Images
Status: completed

## Parent

`.scratch/insightflow-v1/PRD.md`

## What to fix

When entering immersive reading mode on WeChat public account articles, body images can appear missing because the browser may keep a placeholder `src` while the real image URL remains in lazy-loading attributes such as `data-src`.

## Acceptance criteria

- [x] Immersive reading preserves article body images.
- [x] WeChat lazy image URLs from `data-src` replace placeholder `src` values.
- [x] Lazy `srcset` values are normalized when present.
- [x] Existing direct action, extraction, compile, and build checks still pass.

## Comments

- Root cause found on 2026-06-11: `readingSession.cjs` only copied lazy image URLs into `src` when `src` was absent. If WeChat or the browser had already set a transparent placeholder `src`, the immersive overlay kept the placeholder instead of the real `data-src` image.
- Fixed on 2026-06-11: image sanitization now prefers lazy-loading image attributes for `img` and `source` elements before rendering the immersive article.
