# Architecture and decisions

## Decisions

### AD-3 — Board interface
Status: accepted first visual direction. Choice: an airy, welcoming study-board with a clear task hierarchy. Why: the board needs the strongest position while the selected-square status stays easy to find. Alternative considered: dense, full-bleed controls; rejected because it crowds the board. Scope: the local board screen.

#### Art direction
Tone: calm, tactile and lightly playful. Keep the board central and the status quieter. Use available system-ui sans-serif type.

#### Task hierarchy
Keep the board central and the status quieter. Keep the heading and current selection legible without competing with the board.

#### Design system and tokens
Use --page #eef7fb, --surface #fffdf8, --ink #19302e, --board-light #e8f1ff, --board-dark #355b88, --accent #d54e8b, --focus #2d4c77. Use 0.5rem, 1rem and 1.5rem spacing; 0.75rem control radius.

#### Components and composition
The content column is at most 44rem. The board is at most 34rem, uses an equal 8 by 8 grid with a 1:1 overall ratio, and remains the focal surface. Place selection status below it with 1rem separation; controls follow.

#### Theme
Light is the default; retain a dark option with #101d2b canvas and #e9f1fa text. Focus is a visible 3px outline using #2d4c77; selected squares use #d54e8b.
