# UI art-direction side study — 2026-11-05

Pilot the owner-selected C direction: concrete art direction plus an explicit
light Gemini reference. Three anonymous model reviews preferred B on the initial
briefs, but the owner chose C after inspecting the gallery. Preserve that
disagreement; model taste does not override the owner’s preference. The owner
then requested a slick chat workspace comparison using Buzz and Slack as
functional references. This is retained learning, not a shipped prompt change
or a reliability benchmark.

The owner asked for side experiments to elicit a modern, elegant interface,
especially for games, and clarified a mostly light Google/Gemini-like preference.
All candidate prompts, generated HTML, captures and evidence remain outside the
source tree. No default, baseline, model, skill, stage, loop or integration changed.

## Experiment and result

The twelve frozen direct-generation trials use four briefs and three arms:

| Arm | Content |
| --- | --- |
| A | Adapted current UI obligations plus a mostly-light preference |
| B | A plus concrete focal task, typography, spacing, palette/surfaces, shape hierarchy and a useful visual signature |
| C | B plus an explicit light Gemini / Material 3 Expressive target |

A already includes the current guide's optional Material/Gemini principles.
Only B's added block is brand-free. This does not isolate all brand mentions, each
instruction's causal effect, or prompt length. A is a direct-prototype proxy,
not an actual ShipLoop stage execution.

| Brief | Anonymous visual ranking, decoded | A bounded checks | B bounded checks | C bounded checks |
| --- | --- | --- | --- | --- |
| Chess opening study | B, C, A | 15/15 | 15/15 | 15/15 |
| Checkers opening study | B, A, C | 15/15 | 15/15 | 15/15 |
| Greenfield notes workspace | B, C, A | 12/13 | 13/13 | 13/13 |
| Team-and-agent chat workspace | B, A, C | 14/14 | 13/14 | 14/14 |

Two direct samples have observed interaction/state defects: A's notes filter keeps
hidden rows visible, and chat B shows ‘No messages found’ alongside seven messages.
A also has an overlapping desktop note card. Ten of twelve direct samples pass
all bounded browser checks. Secondary-text contrast spot checks found issues
in seven of the initial nine prototypes; gradients, opacity, shadows and icons
are excluded, so these
are not full accessibility audits. A zero-finding sample is not conformance.

The parent agrees with B's stronger composition, particularly its compact mobile
notes selector, but does not accept a reviewer's inference that blue/lavender
necessarily fits Gemini less well. C's cool palette can fit that reference. Model
taste remains triage; the owner’s actual choice is C. No universal Google-fidelity
result is claimed.

An additional isolated two-session probe gives B to a planner, then only its
326-word AD-1, the functional brief and shared UI obligations to a fresh builder.
The separate handoff page passes 15/15 bounded checks. The specified canvas
`#F6F4EF`, board colors `#718779` / `#E8E1D4`, 32 px heading and 32 SVG pieces reach
the render. Its finish is plainer than direct B. This proves one concrete-record
handoff works; it does not prove the visual gain survives real ShipLoop navigation.

## Chat extension after the owner chose C

C also produces a convincing chat surface: a pale lavender canvas, compact channel
navigation, readable author groups, a labeled agent result, attachment and anchored
composer. It passes 14/14 bounded checks, including local send, keyboard send,
channel/draft retention, reactions, search, thread replies and Escape/focus return.
At 1440x1000 and 390x844, in both themes, the composer stays within the viewport
without horizontal overflow. These checks do not establish remote delivery, real
agent work, full keyboard coverage or accessibility conformance.

The key transferable instruction is product-specific composition. Apply the same
visual direction to different working surfaces: board and turn state for games;
compact message groups, reachable composer, channels and threads for chat. The
chat brief explicitly protects readable density and the first screen’s work area.
`PROMPT-RECIPE.md`, `prompts/C.md` and `inputs/chat.md` retain the reusable recipe
and exact tested wording. A shortened replacement was not tested.

[Buzz’s public preview](https://buzz.xyz/) supplied interaction references for
people and agents sharing conversations and work artifacts.
[Slack’s quick-start guide](https://slack.com/help/articles/360059928654-How-to-use-Slack--your-quick-start-guide-3)
supplied channel, message, thread and search vocabulary. No private workspace was
accessed. Their facilities informed the brief; the owner’s chosen Gemini direction
informed appearance.

The fresh anonymous chat reviewer also ranks B first, then A and C. This remains
model taste, not a replacement for the owner’s choice; the owner has not yet ranked
the chat samples. C’s seed date incorrectly says Wednesday for November 5, 2026,
which is Thursday. Original outputs remain intact. Some secondary text appears
faint; no chat contrast audit was run. Screenshot clipping at a scrolling message
viewport’s composer boundary does not by itself prove inaccessible content.

Chat probes ran through CUA with separate local origins per arm. Initial focus
instrumentation rejected a valid box-shadow ring; initial mobile navigation
confused DOM visibility with an on-screen drawer control. Corrected checks ran
consistently on all three arms. Original reports and corrections are retained in
`review/chat-probe-corrections.md` and the final JSON evidence.

## Decision and next useful validation

Keep the explicit design choices in an existing first-UI AD record and carry that
record to implementation. Preserve established product identity and components.
Use the requested light Gemini-like profile as project/request guidance; do not
replace product-specific design with a mandatory global palette or toolkit.

The external study includes the full tested B and C prompts, an untested compressed
generic version and an unapplied minimal patch. The patch adds 27 characters to
the existing first-UI-step clause to name art direction and task hierarchy. Its
baseline is `1178fcfb4195add953fe9fbb011ef3d5479e8d03`; it is not ready to ship on
the strength of these trials. A real UI packet must establish required-text
placement and optional-block retention on both routes. A live UI task on exact
integrated wording and owner acceptance of that result are still needed. No global default or loop policy was changed.

Google's guidance supports hierarchy through color, shape, scale and grouping,
and purposeful motion, while retaining clarity and user control. It also records
preferences for calmer expressive variants. Those principles informed the added
block. Sources: [Google expressive-design research](https://design.google/library/expressive-material-design-google-research)
and [Gemini visual design](https://design.google/library/gemini-ai-visual-design).
The separation of appearance and functional evidence is also supported by
[Anthropic's application-harness research](https://www.anthropic.com/research/harness-design-long-running-apps).

## Evidence and limitations

Evidence root:
`/Users/dadleet/Documents/Codex/experiments/shiploop-ui-prompt-20261105/`

- `index.html` is the local comparison gallery; `REPORT.md` contains the fuller
  analysis and restart command. Active server during the study:
  `http://127.0.0.1:53113/`, bound to loopback only.
- `manifest.json` and `provenance.json` bind the source revision, frozen briefs and
  HTML hashes. `prompts/`, `inputs/`, `runs/` and `handoff/` retain the actual inputs
  and unchanged generated outputs.
- `screenshots/v3/` uses 1440x1000 and 390x844 captures in light and dark themes.
  The initial briefs use fresh browser contexts; chat uses CUA and separate origins.
  `review/final/` contains the bounded browser results;
  `review/*-visual-review.json`, `review/blind-map.json` and
  `review/chat-blind-map.json` retain the anonymous
  review and decoding. `review/handoff-token-check.json` holds measured carry-through.
- Native generation and review used the same host role configurations within
  each role. Exact served model, sampling settings, reasoning tokens and total
  tool-token costs were not exposed. Isolation was instruction-level. No
  cross-model generality or meaningful concurrent latency comparison is claimed.
- One sample per arm per brief, two related board layouts, no repeats, and model
  reviewers are insufficient to establish reliability or statistical significance.
  No real ShipLoop navigation, host refresh, recovery, deployment or E2E ran.
- The browser probe exposed two apparatus errors, both retained: resized dark-phone
  captures duplicated sections, resolved with fresh contexts; a notes save check
  assumed filtering preserved selection, resolved by fresh state and title identity
  for all arms. B's apparent save failure was not a product defect. Original
  evidence is preserved beside the corrections.
- Contrast instrumentation initially skipped all text under ancestor gradients,
  then mishandled resolved sRGB colors. The corrected partial audit is
  `review/contrast-audit.json`; earlier output remains retained and is superseded.
- The gallery's four scenario controls, four capture modes, twelve direct samples
  and narrow layout
  were rendered and checked. No source-code test bank or CI was run for this
  documentation-only retention.

Opus review completed successfully with verified `claude-opus-5-5`, xhigh and no
fallback; JSON and transcript are under `advisor/`. Advice arrived after initial
generation began. Adopted its scope limits, two-session handoff and broader
captures. Its proposed 45-plus-run release benchmark was deferred as larger than
the requested side experiment. No extra obligations were inferred from unrelated
memory references in that advice.

Historical decisions read in full and preserved:

- `5a65d62cf65c3cfacdae456170db9b256cebce4e`: observable UI criteria, with no UI
  model run measured; packet-head pressure moved the design system to the first UI step.
- `9d958312e66ed299ec93780d8670135040aae669`: ambitious evolution within existing
  systems, Google/Gemini guidance, and a separation between planning and rendered proof.
- `be3ed4db54bcd1cfab6258eaf0d84a04f7131ac1`: existing UI ownership and evidence
  boundaries; rendered state is not persistence or identity readiness.
- `855040644721fd5451c3fd86e522e4499a8ebcad`: printed guidance locators do not prove
  consumption; accepted requirements cannot be redefined by passing tests.

Concurrent commits advanced the checkout through
`4a72cf2a21d9091b423c8cc34730ea2c9d587e14`; its full ownership/card-size learning
message was read, and it does not change this study’s frozen baseline. The
pre-existing `.opencode/` directory belongs to other work. This study did not
alter or stage those sources. The document is retained learning; experimental code and unaccepted prompt candidates remain outside main.
