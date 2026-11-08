# Architecture and decisions

## Decisions

### AD-1 — Board interface
Status: accepted first visual direction.

#### Design system and tokens
Use --page #f5f1e8, --surface #fffdf8, --ink #19302e, --board-light #e9dfcb, --board-dark #356f66, --focus #2d5d57; use system-ui.

#### Components and composition
The board maximum is 32rem. Place selection status below the board with a 1rem gap.

#### Theme
Dark is the default using #17201f; a light theme remains available.
