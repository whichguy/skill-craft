# Product specification

## Existing behavior
The local 8×8 board has 64 selectable squares. Selecting one announces its algebraic coordinate in the polite status line; Reset clears the selection. The existing suite runs with `node --test`.

## Appearance
AD-2 in `docs/shiploop/architecture.md` records the accepted board direction, selected-square summary placement, tokens and themes.

## Requirements
- R-1: Move the existing polite selection status immediately below the board and use it as the selected-square summary. It shows the selected coordinate and returns to “Choose a square” when Reset is used.
- R-2: Preserve all 64 selectable local squares, the existing selection announcement and reset behavior, and the existing node:test suite.

## Request (verbatim)

> This repository contains a local 8×8 board with square selection, an existing polite status above the board, and Reset. Move that existing status immediately below the board and use it as the selected-square summary; keep its selected-coordinate announcement and Reset’s ‘Choose a square’ prompt. R-1: Use the accepted board direction recorded in product documentation to shape the summary and plan a rendered browser check at narrow and wide widths in light and dark themes. R-2: Preserve all 64 selectable local squares, the existing selection announcement and Reset behavior, and the existing node:test suite. Stay local, with no dependencies or external service.
