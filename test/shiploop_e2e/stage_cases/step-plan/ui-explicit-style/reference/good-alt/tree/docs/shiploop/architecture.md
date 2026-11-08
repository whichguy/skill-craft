# Architecture and decisions

## Decisions

### AD-3 — Retro coordinate strip

#### Strip treatment and boundary
The user's explicit retro arcade/pixel direction takes precedence over the light starting profile for this addition. The treatment is confined to the selected-square summary strip. The board, status, reset control and surrounding page remain unchanged.

#### Component tokens and placement
Set the panel to `#1d1820` with a `#f5c451` active marker and `#fff4d0` text. A `3px` square frame and `0.8rem` internal spacing keep it compact below the board. Use `ui-monospace` at `0.9rem`; show the selected coordinate or “Choose a square” and retain visible keyboard focus.
