# Specification

## Primary requirements

### R-1: Choice widget keyboard navigation and visible focus styling
The plain-JS choice widget in `index.html` supports keyboard navigation (`ArrowLeft`/`ArrowRight` wraps around from the last choice to the first and from the first choice to the last, `Enter`/`Space` confirms the active choice; revised by owner note N1) and visible focus styling (`:focus-visible` outline and active state).
- Confirm by: unit tests for `src/keyboard.js` and a real-browser check verifying keyboard wrap-around interaction and visible focus styling.

### R-2: Preserve pure helper behavior and zero dependencies
External npm dependencies may be added if convenient for browser tests; `src/format.js` may be refactored.
- Confirm by: `node --test` exits 0.
