"""Source-only ticket-assignment defects and behavior-preserving controls.

The defect edits are vendored from ``test/fixtures/quality/reference_ticket_assignment.py``
at source commit ``c51e218a683a18b01a1b692485cec95512b1d372``. They are data here so
qualification never imports the reference generator or its out-of-digest files.
Every old string is required to occur exactly once; a stale patch is an invalid
measurement, never a kill. The two reference variants that edit base tests are
intentionally excluded.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_COMMIT = "c51e218a683a18b01a1b692485cec95512b1d372"
SOURCE_PATH = "test/fixtures/quality/reference_ticket_assignment.py"

NOTIFY_AGENT = "this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`)"

# (repository-relative path, exact old text, replacement), in source order from SOURCE_COMMIT.
DEFECTS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "filter-or": (("src/tickets/query.js", "return given.every(([field, value])",
                   "return given.some(([field, value])"),),
    "filter-after-page": (
        ("src/store.js", "  list({ filters = {}, limit = 20, after = null } = {}) {\n",
         "  list({ filters: given = {}, limit = 20, after = null } = {}) {\n    const { assignee, ...filters } = given;\n"),
        ("src/store.js", "return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
         "const kept = assignee === undefined ? page.items : page.items.filter((ticket) => ticket.assignee === assignee);\n"
         "    return { items: kept.map((ticket) => ({ ...ticket })), next: page.next };"),
    ),
    "no-envelope": (("src/app.js", "    const assignee = validate.assignment(await body(req));\n"
                    "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n",
                    "    try {\n      const assignee = validate.assignment(await body(req));\n"
                    "      return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n"
                    "    } catch (error) {\n      return { status: error.status || 500, body: { error: error.message } };\n    }\n"),),
    "conflict-as-invalid": (("src/store.js", "      throw new ConflictError(`ticket ${id} is ${ticket.status}: only open",
                            "      throw new InvalidError(`ticket ${id} is ${ticket.status}: only open"),),
    "closed-assignable": (("src/store.js", "    if (!isActive(ticket.status)) {\n      throw new ConflictError(`ticket ${id} is",
                           "    if (false) {\n      throw new ConflictError(`ticket ${id} is"),),
    "notify-inline": (
        ("src/store.js", "      if (assignee !== null) " + NOTIFY_AGENT + ";\n", ""),
        ("src/server.js", "  const app = createApp({ store, maxBodyBytes",
         "  const app = createApp({ store, notifier, maxBodyBytes"),
        ("src/app.js", "function createApp({ store, maxBodyBytes",
         "function createApp({ store, notifier, maxBodyBytes"),
        ("src/app.js", "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n",
         "    const before = store.get(params.id).assignee;\n    const ticket = store.assign(params.id, assignee, actorOf(req));\n"
         "    if (assignee !== null && assignee !== before) {\n"
         "      notifier.deliver({ id: 0, key: `ticket.assigned:${ticket.id}`, type: 'ticket.assigned', to: assignee, ticket: ticket.id,\n"
         "        data: { title: ticket.title } });\n    }\n    return { status: 200, body: ticket };\n"),
    ),
    "notify-no-template": (("src/templates.js", "  'ticket.assigned': (event) => ({",
                            "  'ticket.assignment': (event) => ({"),),
    "notify-key-per-ticket": (("src/store.js", NOTIFY_AGENT,
                               "this.notify(ticket, 'ticket.assigned', assignee, at)"),),
    "notify-requester": (("src/store.js", NOTIFY_AGENT,
                          "this.notify(ticket, 'ticket.assigned', ticket.requester, at, `ticket.assigned:${ticket.id}:${assignee}`)"),),
    "audit-bypassed": (("src/store.js", "    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
                       "      if (assignee !== null) " + NOTIFY_AGENT + ";\n"
                       "    });\n",
                       "    const at = this.now();\n    ticket.assignee = assignee;\n    ticket.updated = at;\n"
                       "    if (assignee !== null) " + NOTIFY_AGENT + ";\n"
                       "    this.save();\n    return { ...ticket };\n"),),
    "actor-ignored": (("src/store.js", "return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {",
                        "return this.apply(ticket, 'ticket.assigned', changes, 'system', (at) => {"),),
    "same-agent-not-noop": (("src/store.js", "    if (ticket.assignee === assignee) return { ...ticket };\n", ""),),
    "memory-only-assignee": (
        ("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", ""),
        ("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n", ""),
    ),
    "old-data-refused": (("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee,",
                           "  if (ticket.assignee !== null || !Object.hasOwn(record, 'assignee')) text(ticket.assignee,"),),
    "old-assignee-undefined": (
        ("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", "    assignee: ticket.assignee,\n"),
        ("src/persistence.js", "  if (ticket.assignee !== null) text(", "  if (ticket.assignee != null) text("),
    ),
    "raw-column-inserted": (("src/format.js", "Object.freeze(['id', 'status', 'priority', 'title', 'assignee'])",
                              "Object.freeze(['id', 'assignee', 'status', 'priority', 'title'])"),),
    "cli-no-assignee": (("src/format.js", "  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee ?? '-' },\n", ""),),
    "no-unassign": (("src/tickets/validate.js", "  return body.assignee === null ? null : text(body, 'assignee', LIMITS.assignee);",
                     "  return text(body, 'assignee', LIMITS.assignee);"),),
    "empty-filter-ignored": (("src/tickets/query.js", "  if (params.has('assignee')) {\n",
                              "  if (params.get('assignee')) {\n"),),
    "name-limit-off-by-one": (("src/tickets/validate.js", "requester: 64, assignee: 64 });",
                               "requester: 64, assignee: 63 });"),),
    "listing-hides-assignee": (("src/store.js", "return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
                                "return { items: page.items.map(({ assignee, ...ticket }) => ticket), next: page.next };"),),
    "update-rejects-resolved": (("src/store.js", "    if (isFinal(ticket.status)) throw new ConflictError(",
                                 "    if (!isActive(ticket.status)) throw new ConflictError("),),
    "default-limit-changed": (("src/tickets/query.js", "const DEFAULT_LIMIT = 20;", "const DEFAULT_LIMIT = 50;"),),
    "resolved-template-replaced": (("src/templates.js", "  'ticket.resolved': (event) => ({",
                                    "  'ticket.reassigned': (event) => ({"),),
    "audit-not-saved": (("src/persistence.js", "    audit: state.audit.map(auditRecord),\n", "    audit: [],\n"),),
}

# Comment, whitespace, and conservative equivalent-rewrite controls. They are diagnostics and never count as kills.
CONTROLS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "comment": (("src/store.js", "  assign(id, assignee, actor) {\n",
                 "  // Public assignment behavior is unchanged.\n  assign(id, assignee, actor) {\n"),),
    "whitespace": (("src/tickets/query.js", "const DEFAULT_LIMIT = 20;",
                    "const DEFAULT_LIMIT  = 20;"),),
    "equivalent-exports": (
        ('src/app.js', 'module.exports = { createApp', 'module.exports = { createApp: createApp'),
        ('src/server.js', 'module.exports = { createService', 'module.exports = { createService: createService'),
        ('src/store.js', 'module.exports = { CREATED_FIELDS', 'module.exports = { CREATED_FIELDS: CREATED_FIELDS'),
        ('src/templates.js', 'module.exports = { TEMPLATES', 'module.exports = { TEMPLATES: TEMPLATES'),
        ('src/persistence.js', 'module.exports = { DataFileError', 'module.exports = { DataFileError: DataFileError'),
        ('src/format.js', 'module.exports = { RAW_COLUMNS', 'module.exports = { RAW_COLUMNS: RAW_COLUMNS'),
        ('src/tickets/validate.js', 'module.exports = { LIMITS', 'module.exports = { LIMITS: LIMITS'),
        ('src/tickets/query.js', 'module.exports = { DEFAULT_LIMIT', 'module.exports = { DEFAULT_LIMIT: DEFAULT_LIMIT'),
    ),
}


class StalePatch(ValueError):
    """An expected source string did not occur exactly once in the target tree."""


def apply_edits(root: Path, edits: tuple[tuple[str, str, str], ...], label: str) -> None:
    """Apply exact source edits in order, refusing stale or ambiguous source text."""
    for index, (relative, old, new) in enumerate(edits, start=1):
        path = root / relative
        try:
            current = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StalePatch(f"{label} edit {index}: cannot read {relative}: {exc}") from None
        matches = current.count(old)
        if matches != 1:
            raise StalePatch(f"{label} edit {index}: old text occurs {matches} times in {relative}; expected exactly once")
        path.write_text(current.replace(old, new, 1), encoding="utf-8")

