## Fixed

- C-265 | Reloading immediately after a scroll could discard the latest bookmark because Chrome had already captured the history entry. The app now saves reading bookmarks in tab-scoped session storage and captures the current position when the page hides. It also reads existing bookmarks from history when no session bookmark is available.

## Disputed

none

## Discoveries

- Chrome can capture the history state for a reload before the outgoing page runs its lifecycle handlers. | Observable: Scroll to an older message and immediately reload. The outgoing handler can read its updated history state, while the replacement document receives the earlier state. | Why: A browser probe recorded the correct bookmark during both visibilitychange and pagehide, yet the replacement document opened at the newest message.
