---
bump: minor
---
- **eslint now applies its own fix too**, through a separate `--fix-dry-run --format json` call made only when
  fixing is allowed this pass (its regular report call stays unchanged and always runs, since fix-dry-run's own
  messages are numbered against the hypothetical fixed text, not the real file). A fix to a plain `.js`/`.mjs`/
  `.cjs` file is additionally checked with `node --check` before it is applied, written beside the real file so
  Node's module-type resolution matches; `.ts`/`.tsx`/`.jsx`/`.vue` rely on the same scope and line-ending guards
  every other fixable tool already has. This completes the formatter-autofix round in
  `discovered-formatter-autofix.md`: eslint was the one tool in that round needing its own fix call.
