# Product specification

## Existing behavior
The local 8×8 board has 64 selectable squares. Selecting one announces its algebraic coordinate in the polite status line; Reset clears the selection. The existing suite runs with `node --test`.

## Appearance
AD-2 in `docs/shiploop/architecture.md` records the accepted board direction, existing-status placement, tokens and themes.

## Requirements
- R-1: Move the existing polite status immediately below the board so it serves as the selected-square summary. It shows the selected coordinate and returns to “Choose a square” when Reset is used.
- R-2: Preserve all 64 selectable local squares, the existing selection announcement and reset behavior, and the existing node:test suite.

## Request (verbatim)

> This repository contains a local 8×8 board with square selection, an existing polite selection status, and Reset. Move the existing status immediately below the board so it serves as the selected-square summary: it shows the selected coordinate and returns to “Choose a square” when Reset is used. R-1: Use the accepted board direction recorded in the product documentation to shape the moved status and plan a rendered browser check at narrow and wide widths in light and dark themes. R-2: Preserve all 64 selectable local squares, the existing selection announcement and reset behavior, and the existing node:test suite. Stay local, with no dependencies or external service.
