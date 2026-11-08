# Architecture and decisions

## Decisions

### AD-3 — Local chat interface
Status: accepted first visual direction. The local chat uses a Use a centered conversation chooser above the active thread, with a quiet side rail at wide widths. Scope: this local chat screen.

#### Art direction
Keep the interface calm, clear and readable. Use system-ui sans-serif.

#### Task hierarchy
Make conversation switching easy to scan while the active message thread and composer lead the task.

#### Design system and tokens
Use --page #f1f8f5, --panel #ffffff, --ink #203731, --muted #60756f, --accent #138a78, and --focus #0d665b. The content maximum is 68rem. Use 0.5rem, 1rem and 1.5rem spacing and a 0.75rem radius.

#### Components and composition
Use a centered conversation chooser above the active thread, with a quiet side rail at wide widths. Mark the selected conversation with an accent border. Keep the composer available after the messages and avoid horizontal overflow.

#### Theme
Light is the default; retain a dark option with #18332f canvas. The dark panel is #24423d with #e6f0ec text. Keep selected conversation and keyboard focus distinguishable.
