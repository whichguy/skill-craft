# Product specification

## Current request

This board already has a thin AD-2 in docs/shiploop/architecture.md. Move the existing selected-square status immediately below the board as a summary; it shows the selected coordinate and returns to ‘Choose a square’ on Reset. Complete AD-2 in place with the missing implementation-ready composition, type, theme, and rendered-check details. Preserve its AD-2 ID and every value already recorded. Keep the board behavior and node:test suite. Stay local, with no dependencies or external service.

## Requirements

- R-1: Move the selected-square summary below the board; complete the existing AD-2 without changing its ID or accepted values.
- R-2: Preserve local selection, coordinate announcements, Reset and node:test coverage; add no dependencies or external service.
