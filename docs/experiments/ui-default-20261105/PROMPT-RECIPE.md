# A light, expressive default for new interfaces

This is a copyable design-phase recipe distilled from the experiments. ShipLoop implements the same direction across its specification, planning and UI guidance; this is not a verbatim dump of one runtime packet.

```text
For a new graphical interface, fill unspecified visual choices from the light Google Gemini look and feel, using Material 3 Expressive principles. Preserve explicit constraints, established product identity and platform conventions. A new screen inside an existing product inherits that product’s identity. Start a new web UI in light mode and provide a dark option unless those constraints establish another appearance policy.

Create a luminous canvas, tonal layered surfaces, deliberate rounded shapes, friendly precise sans-serif type, confident primary actions and purposeful motion. Use available local fonts and readable fallbacks. Give the primary activity the strongest position and visual weight. Choose one useful visual detail that gives this product character. No particular palette, layout or UI toolkit is mandatory.

Make concrete design decisions before building: typography and spacing, semantic foreground/background roles, where tinted surfaces appear, shape and depth, important interaction states, and the phone composition. Record the chosen reference and appearance policy. A palette list or adjectives such as modern and premium are insufficient.

Carry the applicable decision sections and a few observable visual anchors into each UI step’s acceptance criteria. The criterion itself must say what the rendered result should show. Implement those selected choices. Functional counts and interactions do not establish visual quality.

Inspect the rendered product at desktop and phone widths, in both themes, including text contrast, visible keyboard focus, empty/selected/disabled states and the primary action. Correct departures through the existing workflow. Keep any condition that cannot be verified explicitly open, with what would confirm it; do not report it as passed.
```

For chat, make readable message groups, threads, attachments and the reachable composer dominant. Use available desktop space for work and one focused conversation on a phone. For games, prioritize the board, well-resolved pieces, player/turn state and compact controls; verify the geometry as well as the move rules. Other applications should derive their hierarchy from their own primary task.

The experiments support using explicit direction and concrete handoffs. They do not establish a universal success rate: retained outputs exposed contrast, focus, mobile overlap and board-geometry failures even when functional checks passed.
