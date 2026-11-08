# Architecture and decisions

## Decisions

### AD-2 — Board interface
Status: accepted. Choice: a calm, tactile board with the board as the primary activity and its selected-square summary easy to find. Scope: the local board.

#### Art direction
Use a quiet, readable interface with a light default and a dark option. Use system-ui sans-serif type.

#### Task hierarchy
The board is primary. Keep selection status, controls and instructions readable without competing with play.

#### Design system and tokens
Use --page #f4f1e9, --surface #fffdf8, --ink #19302e, --muted #596d68, --accent #bb633e, --board-light #e7dcc5, --board-dark #34746b, --selected #f3c15b, and --focus #214c46. Use 0.5rem, 1rem and 1.5rem spacing and a 0.75rem radius. Set the content maximum to 44rem and the board maximum to 32rem.

#### Components and composition
Center the board as the primary activity. Use an equal 8 by 8 grid with a 1:1 ratio. Put the selected-square summary immediately below the board; cap it at 32rem and separate it from the board by 1rem. Keep controls available after the summary.

#### Theme
Light is the default with #f4f1e9 page and #19302e text. Offer a dark option with #17201f canvas, #212d2a surfaces, #f4f1e9 text and #becac4 muted text. Use a visible 3px focus ring in #214c46 in light mode and #f3c15b in dark mode.

### AD-3 — Replacement board
A new replacement identity.
