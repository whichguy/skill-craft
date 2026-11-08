# Architecture and decisions

## Decisions

### AD-1 — Local chat interface
Status: accepted first visual direction. The local chat uses a At wide widths, place the conversation list beside the message panel. At narrow widths, stack them in that order. Scope: this local chat screen.

#### Art direction
Keep the interface calm, clear and readable. Use system-ui sans-serif.

#### Task hierarchy
Make conversation switching easy to scan while the active message thread and composer lead the task.

#### Design system and tokens
Use --page #f5f2eb, --panel #ffffff, --ink #24313d, --muted #5a6874, --accent #4f66bf, and --focus #344e9c. The content maximum is 72rem. Use 0.5rem, 1rem and 1.5rem spacing and a 0.75rem radius.

#### Components and composition
At wide widths, place the conversation list beside the message panel. At narrow widths, stack them in that order. Mark the selected conversation with an accent border. Keep the composer available after the messages and avoid horizontal overflow.

#### Theme
Dark is the default; light mode is available; retain a dark option with #18222e canvas. The dark panel is #212f3d with #e7edf5 text. Keep selected conversation and keyboard focus distinguishable.
