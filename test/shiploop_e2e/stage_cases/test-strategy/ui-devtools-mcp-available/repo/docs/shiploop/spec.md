# Specification

## Primary requirements

### R-1: Choice widget keyboard navigation and visible focus styling
The plain-JS choice widget in `index.html` supports keyboard navigation (`ArrowLeft`/`ArrowRight` to move selection across options, `Enter`/`Space` to confirm the active option) and visible focus styling (`:focus-visible` outline and active state).
- Confirm by: unit tests for pure navigation logic and an automated real-browser check verifying keyboard interaction and computed visible focus styling.

### R-2: Preserve pure helper behavior and zero dependencies
Preserve existing pure helper behavior in `src/format.js` and keep `node --test` passing with zero external npm dependencies.
- Confirm by: `node --test` exits 0 with all existing tests passing.
