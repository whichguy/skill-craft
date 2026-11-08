# Architecture and decisions

## Decisions

- **AD-1 — Selected-square summary strip**

#### Explicit direction and scope
The user's explicit retro arcade/pixel direction takes precedence over the light expressive starting profile for this authorized addition. The treatment is confined to the selected-square summary strip immediately below the board. Keep the 64-square board, controls, current status and rest of the page unchanged.

- **Strip tokens and placement**: Use a charcoal panel `#25202a`, warm signal amber `#efb849`, and cream text `#fff1c9`. Set a square `2px` outline, `0.75rem` inner spacing, and an available `ui-monospace` font at `0.875rem`. Keep the coordinate readable and the keyboard focus visible. The strip sits directly below the board; its empty state says “Choose a square” and its selected state shows the coordinate. The pixel-inspired frame and compact coordinate label give the strip its character without restyling its neighbors.
