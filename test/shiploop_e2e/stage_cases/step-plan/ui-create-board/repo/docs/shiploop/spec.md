# Product specification

## Existing behavior
The local board has 64 square controls. Selecting one announces its algebraic coordinate in the status line; Reset clears the selection. node --test is the existing suite.

## Appearance
No appearance requirement or accepted visual identity has been recorded. The current stylesheet is a plain functional starter, not a product design.

## Requirements
- R-1: Give the local board its first clear, responsive visual direction. Preserve a readable board, selection status, and reset control.
- R-2: Keep all 64 local squares selectable, announce the selected coordinate, clear selection with Reset, and retain the existing node:test suite.

## Request (verbatim)

> This repository contains a local 8×8 board demo with a plain starter screen, square selection, a polite selection status, and Reset. R-1: Give it its first designed interface so the board is clear, responsive, keyboard-usable, and easy to read. Choose a visual direction from the product context; no brand or palette is prescribed. Plan a rendered browser check at narrow and wide widths in light and dark themes. R-2: Keep the square-selection and reset behavior and existing node:test suite. Stay local, with no dependency or external service.
