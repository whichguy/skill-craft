# Product specification

## Existing behavior
The local board has 64 square controls. Selecting one announces its algebraic coordinate in the status line; Reset clears the selection. `node --test` is the existing suite.

## Existing appearance
No accepted product-wide art direction is recorded. The board and its controls are a functional starter; this feature request styles only the new summary strip.

## User request (verbatim)
> This local 8×8 board has a selection status. Add a selected-square summary strip immediately below the board; when Reset is used, return it to ‘Choose a square’. R-1: Show the selected coordinate and clear it on reset. R-2: Give only that summary strip an explicitly retro arcade/pixel-inspired appearance; keep the board, controls, and rest of the page as they are. Stay local; no dependencies or external services.

## Requirements
- **R-1 — new feature:** Show the selected square's coordinate in the summary strip below the board, and clear the strip to “Choose a square” on Reset.
- **R-2 — existing behavior and requested scope:** Apply the requested retro arcade/pixel appearance only to the summary strip. Keep the existing board, controls, status announcement, reset behavior, and rest of the page as they are.
