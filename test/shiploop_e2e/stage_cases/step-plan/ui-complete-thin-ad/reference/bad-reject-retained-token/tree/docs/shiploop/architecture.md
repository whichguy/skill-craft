# Architecture

## Decisions

### AD-2 — Board interface

Status: accepted identity preserved; the requested summary placement is authorized.

#### Appearance and tokens

Do not retain --page #f4f1e9; replace it with #000000 (see styles.css).

Keep the warm green identity and its existing roles: --page #f4f1e9, --surface #fffdf8, --ink #19302e, --muted #596d68, --accent #bb633e, --board-light #e7dcc5, --board-dark #34746b, --selected #f3c15b and --focus #214c46. Use system-ui, sans-serif with .5rem, 1rem and 1.5rem spacing and .75rem corners. Content remains capped at 44rem; the board remains square and at most 32rem wide. A distinct selection ring keeps the tactile board legible without adding another brand.

#### Summary composition

Keep the board as the primary task in a centered column. Move the existing polite status directly below the board in normal flow, at a 1rem gap and up to 32rem wide; Reset follows it. The status uses the --surface fill and --ink text. It shrinks within a narrow screen and never overlays squares. No state behavior or unrelated component is changed.

#### Theme and observations

The light palette stays the default. The existing theme-dark class selects --page #17201f, --surface #212d2a, --ink #f4f1e9, --muted #becac4 and --focus #f3c15b. Keyboard focus remains 3px and selection stays separate. Observe the summary, square geometry, overflow, focus and select/reset in a browser at 390x844 and 1440x1000 in both themes.

#### Rationale and alternatives

The existing identity is accepted and the request is a small addition. A new palette or sidebar would expand that request and displace the board; retain the current system and complete its missing documentation instead.
