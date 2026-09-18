# Field Notes baseline design

## Scope and accepted premise

This is a local browser record for field researchers reviewing and correcting two
notes. Its single job is to make the list, read, edit, save, cancel, back, and
account-selection journey clear before the asynchronous feature work begins.

The accepted palette and component vocabulary from `SPEC.md` win over a redesign:
navy `#15324f`, amber `#c08722`, white cards, and a pale blue-gray ground. The
page has no external assets, frameworks, or runtime installation because the
static CSP deployment fixture does not need them.

## Compact design plan and critique

| Layer | Decision |
| --- | --- |
| Color | Navy ink (`#15324f`), deep navy (`#0c243b`), amber locator (`#c08722`), pale amber (`#f6e9cc`), paper (`#ffffff`), mist (`#eef3f7`). |
| Type | Georgia is reserved for record titles; system sans-serif carries reading, controls, and utility labels. |
| Layout | A masthead names the notebook and account, a paper panel carries the list or record, and a fixed action bar keeps editing controls in reach. |
| Signature | Amber survey marks and a faint vertical field-rule make the record feel like a deliberate field folio without adding decorative noise. |

The first pass risked using generic dashboard cards. The revised treatment makes
the page a field notebook: its labels name records and folios, the single amber
mark locates a record, and the narrow rule is a physical cue rather than a
generic metric accent. The rest stays quiet so the note text remains the focus.

## UI premises recorded for the feature plan

### Component layer

The durable baseline components are the account selector, note-list buttons,
detail record, stable textarea editor node, confirmed-note view, and edit/save/
cancel/back controls. Buttons keep native keyboard and touch semantics, focus
is visible, and the editor lives in a scrollable detail area.

### Interaction-model layer

The accepted journey is account → list → detail → edit → save or cancel → back.
The server response supplies confirmed content and revision; the browser keeps
only the current view and working text in memory. Baseline saves wait for the
single POST response, report clear outcomes through the save-status region, and
do not implement reconciliation, retry, conflicts, lifecycle handling, or
export notifications.

### Brand and skin layer

Navy is the stable research ink; amber marks a location or primary save action.
White paper panels and Georgia titles distinguish the field record from the
pale working surface. The visual system works without a component framework,
custom font, or external asset, so it remains compatible with the fixture CSP.

## Applied frontend-design guidance

Guidance source during the recorded study: the locally available `frontend-design` skill. This is provenance; browser reruns do not invoke that skill.

SHA-256: `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`.

The guidance informed the compact token plan, a single purposeful signature,
plain action labels, responsive layout, visible focus, and restrained motion.
The baseline deliberately adds no motion because it has no asynchronous state
cue yet; later feature work may add a reduced-motion equivalent only when a
visible state change needs one.
