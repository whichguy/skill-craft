# Specification

## Primary requirements

### R-1: Choice widget keyboard navigation and visible focus styling
The plain-JS choice widget in `index.html` supports keyboard navigation (`ArrowLeft`/`ArrowRight` moves selection clamped at the first and last choices, `Enter`/`Space` confirms the active choice) and visible focus styling (`:focus-visible` outline and active state).
- Confirm by: unit tests for `src/keyboard.js` and a real-browser check verifying keyboard interaction and visible focus styling.

### R-2: Preserve pure helper behavior and zero dependencies
Preserve existing pure helper behavior in `src/format.js` and keep `node --test` passing with zero external npm dependencies.
- Confirm by: `node --test` exits 0 with all existing tests passing.
