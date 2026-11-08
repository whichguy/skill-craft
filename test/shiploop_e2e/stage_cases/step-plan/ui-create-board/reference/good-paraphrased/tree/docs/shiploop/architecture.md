# Architecture and decisions

## Decisions

### AD-4 — Board interface

Status: accepted first interface for the local board.

#### Palette and typography

The light-first default uses --page #f6f3ea, --surface #fffdf8, --ink #20332e, --board-a #e9dfca, --board-b #337267 and --focus #2f5c54. Use font-family: "Atkinson Hyperlegible", Arial, sans-serif.

#### Board layout

Keep the board square and no wider than 34rem. Place the polite selection status directly below the grid with a 1rem gap and a matching maximum width.

#### Dark theme

The dark option uses --page #18251f, --surface #26352f, --ink #f4f1e8 and --focus #f0b65b. Keep the selection ring visible against both square colors.
