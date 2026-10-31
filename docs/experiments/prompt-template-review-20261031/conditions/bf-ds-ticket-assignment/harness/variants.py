#!/usr/bin/env python3
"""Per-condition product-code variants: id -> [ (note, [ (file, old, new), ... ]), ... ] (first is primary)."""

# ---- anchors in src/store.js (assign) ----
ST = "src/store.js"
APP = "src/app.js"
VAL = "src/tickets/validate.js"
QRY = "src/tickets/query.js"
PER = "src/persistence.js"
FMT = "src/format.js"
TPL = "src/templates.js"
NOT = "src/notifier.js"
WRK = "src/worker.js"
WEEKLY = "scripts/weekly-report.js"

FIND_HEAD = "  assign(id, assignee, actor) {\n    const ticket = this.find(id);\n"
GUARD = ("    if (!isActive(ticket.status)) {\n"
         "      throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer be assigned`);\n"
         "    }\n")
CHANGES = "    const changes = ticket.assignee === assignee ? {} : { assignee: { from: ticket.assignee, to: assignee } };\n"
APPLY = ("    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
         "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);\n"
         "    });\n")
NOTIFY_CALL = "this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`)"
AUDIT_APPEND = "    this.audit.append({ ticket: ticket.id, action, actor, at, changes });\n"

PUT_OLD = ("    const assignee = validate.assignment(await body(req));\n"
           "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n")


def after_guard(extra):
    return (ST, GUARD, GUARD + extra)


def guard_replace(new_guard):
    return (ST, GUARD, new_guard)


def apply_replace(new_apply):
    return (ST, APPLY, new_apply)


def get_id(new):
    return (APP, "  router.get('/tickets/:id', ({ params }) => ({ status: 200, body: store.get(params.id) }));\n", new)


LIST_OLD = "  router.get('/tickets', ({ url }) => ({ status: 200, body: store.list(parseListQuery(url.searchParams)) }));\n"
PATCH_OLD = "    return { status: 200, body: store.update(params.id, patch, actorOf(req)) };\n"
TRANS_OLD = "    return { status: 200, body: store.transition(params.id, to, actorOf(req)) };\n"
POST_OLD = "    return { status: 201, body: store.create(input, actorOf(req)) };\n"

ASSIGNMENT_RETURN = "  return assignee(body.assignee);\n"
HAS_CHECK = ("  if (!Object.prototype.hasOwnProperty.call(body, 'assignee')) throw new InvalidError('assignee is required');\n"
             "  return assignee(body.assignee);\n")

MF = "  const given = Object.entries(filters).filter(([, value]) => value !== undefined);\n  return given.every(([field, value]) => ticket[field] === value);\n"

V = {}

# ---------------- R-1 ----------------
V["R-1.1"] = [("POST /tickets response drops assignee", [(APP, POST_OLD,
    "    const created = store.create(input, actorOf(req));\n    delete created.assignee;\n    return { status: 201, body: created };\n")])]
V["R-1.2"] = [("GET /tickets/:id omits the assignee key while it is null", [get_id(
    "  router.get('/tickets/:id', ({ params }) => {\n    const t = store.get(params.id);\n    if (t.assignee === null) delete t.assignee;\n    return { status: 200, body: t };\n  });\n")])]
V["R-1.3"] = [("GET /tickets items omit assignee while it is null", [(APP, LIST_OLD,
    "  router.get('/tickets', ({ url }) => {\n    const page = store.list(parseListQuery(url.searchParams));\n    for (const item of page.items) if (item.assignee === null) delete item.assignee;\n    return { status: 200, body: page };\n  });\n")])]
V["R-1.4"] = [("PATCH response drops assignee", [(APP, PATCH_OLD,
    "    const updated = store.update(params.id, patch, actorOf(req));\n    delete updated.assignee;\n    return { status: 200, body: updated };\n")])]
V["R-1.5"] = [("transition response drops assignee", [(APP, TRANS_OLD,
    "    const moved = store.transition(params.id, to, actorOf(req));\n    delete moved.assignee;\n    return { status: 200, body: moved };\n")])]
V["R-1.6"] = [("data file omits the assignee key while it is null", [(PER,
    "    tickets: state.tickets.map(ticketRecord),\n",
    "    tickets: state.tickets.map((t) => {\n      const r = ticketRecord(t);\n      if (r.assignee === null) delete r.assignee;\n      return r;\n    }),\n")])]
V["R-1.7"] = [("GET /tickets/:id masks the assignee as null", [get_id(
    "  router.get('/tickets/:id', ({ params }) => {\n    const t = store.get(params.id);\n    t.assignee = null;\n    return { status: 200, body: t };\n  });\n")])]
V["R-1.8"] = [("GET /tickets items mask the assignee as null", [(APP, LIST_OLD,
    "  router.get('/tickets', ({ url }) => {\n    const page = store.list(parseListQuery(url.searchParams));\n    for (const item of page.items) item.assignee = null;\n    return { status: 200, body: page };\n  });\n")])]
V["R-1.9"] = [("unassigning answers null but the store keeps the old name", [(ST, APPLY,
    "    const before = ticket.assignee;\n"
    "    const result = this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
    "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);\n"
    "    });\n"
    "    if (assignee === null) ticket.assignee = before;\n"
    "    return result;\n")])]
V["R-1.10"] = [("load discards the stored assignee", [(PER,
    "  ticket.assignee = assignee(ticket.assignee, `${where}.assignee`, fail);\n",
    "  assignee(ticket.assignee, `${where}.assignee`, fail);\n  ticket.assignee = null;\n")])]
V["R-1.11"] = [("legacy ticket without assignee loads with no assignee value", [(PER,
    "  if (value === undefined) return null;\n", "  if (value === undefined) return undefined;\n")])]
V["R-1.12"] = [
    ("load message no longer names the record", [(PER,
        "    throw fail(`${where} ${error.message.replace(/^assignee /, '')}`);\n",
        "    throw fail(error.message);\n")]),
    ("non-string assignee loads as null instead of being refused", [(PER,
        "  if (value === undefined) return null;\n",
        "  if (value === undefined || (typeof value !== 'string' && value !== null)) return null;\n")]),
]
V["R-1.13"] = [("empty-string assignee loads as null", [(PER,
    "  if (value === undefined) return null;\n", "  if (value === undefined || value === '') return null;\n")])]
V["R-1.14"] = [("over-long assignee loads", [(PER,
    "    return validateAssignee(value);\n",
    "    return typeof value === 'string' && value.length > 64 && value.length < 200 ? value : validateAssignee(value);\n")])]
V["R-1.15"] = [("control-character assignee loads", [(PER,
    "    return validateAssignee(value);\n",
    "    return typeof value === 'string' && /[\\u0000-\\u001f\\u007f]/.test(value) ? value : validateAssignee(value);\n")])]

# ---------------- R-2 ----------------
V["R-2.1"] = [("PUT answers the ticket as it was before the change", [(APP, PUT_OLD,
    "    const assignee = validate.assignment(await body(req));\n"
    "    const before = store.get(params.id);\n"
    "    const after = store.assign(params.id, assignee, actorOf(req));\n"
    "    return { status: 200, body: assignee !== null ? before : after };\n")])]
V["R-2.2"] = [("assign works on a copy: the response changes, the stored ticket does not", [(ST, FIND_HEAD,
    "  assign(id, assignee, actor) {\n    const ticket = { ...this.find(id) };\n")])]
V["R-2.3"] = [("assignment does not move updated", [apply_replace(
    "    const prior = ticket.updated;\n"
    "    const result = this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
    "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);\n"
    "    });\n"
    "    ticket.updated = prior;\n"
    "    return { ...result, updated: prior };\n")])]
V["R-2.4"] = [("assigning an open ticket also moves it to in_progress", [(ST, CHANGES,
    CHANGES + "    if (assignee !== null && ticket.status === 'open') ticket.status = 'in_progress';\n")])]
V["R-2.5"] = [("assignee is validated trimmed but stored as given", [(VAL,
    "  return text({ assignee: value }, 'assignee', LIMITS.assignee);\n",
    "  return text({ assignee: value }, 'assignee', LIMITS.assignee) && value;\n")])]
V["R-2.6"] = [("unknown ticket id on assign answers 400 invalid", [(ST, FIND_HEAD,
    "  assign(id, assignee, actor) {\n    const ticket = this.tickets.get(id);\n    if (!ticket) throw new InvalidError(`${id} is not a ticket`);\n")])]
V["R-2.7"] = [("a body that fails to parse as an object is read as unassign", [(APP, PUT_OLD,
    "    let parsed;\n    try {\n      parsed = await body(req);\n    } catch (error) {\n      parsed = { assignee: null };\n    }\n"
    "    const assignee = validate.assignment(parsed);\n"
    "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n")])]
V["R-2.8"] = [("a missing assignee field is read as null", [(VAL, HAS_CHECK,
    "  return assignee(body.assignee === undefined ? null : body.assignee);\n")])]
V["R-2.9"] = [("an array or object assignee is coerced to text", [(VAL, ASSIGNMENT_RETURN,
    "  return typeof body.assignee === 'object' && body.assignee !== null ? assignee(String(body.assignee)) : assignee(body.assignee);\n")])]
V["R-2.10"] = [("unknown fields on the PUT body are ignored", [(VAL,
    "function assignment(body) {\n  onlyFields(body, ['assignee']);\n", "function assignment(body) {\n")])]

# ---------------- R-3 ----------------
V["R-3.1"] = [("unassigning answers the ticket as it was before", [(APP, PUT_OLD,
    "    const assignee = validate.assignment(await body(req));\n"
    "    const before = store.get(params.id);\n"
    "    const after = store.assign(params.id, assignee, actorOf(req));\n"
    "    return { status: 200, body: assignee === null ? before : after };\n")])]
V["R-3.2"] = V["R-1.9"]
V["R-3.3"] = [("unassigning an unassigned ticket conflicts", [after_guard(
    "    if (assignee === null && ticket.assignee === null) throw new ConflictError(`ticket ${id} has no assignee`);\n")])]

# ---------------- R-4 ----------------
def asg(new_body):
    return (VAL, ASSIGNMENT_RETURN, new_body)

V["R-4.1"] = [("names shorter than 2 characters are refused", [asg(
    "  const named = assignee(body.assignee);\n  if (named !== null && named.length < 2) throw new InvalidError('assignee must have at least 2 characters');\n  return named;\n")])]
V["R-4.2"] = [("a 64-character name is refused on PUT", [asg(
    "  const named = assignee(body.assignee);\n  if (named !== null && named.length >= 64) throw new InvalidError('assignee must be at most 63 characters');\n  return named;\n")])]
V["R-4.3"] = [("an empty string unassigns", [asg(
    "  if (body.assignee === '') return null;\n  return assignee(body.assignee);\n")])]
V["R-4.4"] = [("whitespace-only text unassigns", [asg(
    "  if (typeof body.assignee === 'string' && body.assignee !== '' && body.assignee.trim() === '') return null;\n  return assignee(body.assignee);\n")])]
V["R-4.5"] = [("the PUT length limit is 128", [asg(
    "  return body.assignee === null ? null : text(body, 'assignee', 128);\n")])]
V["R-4.6"] = [("tabs in the name become spaces", [asg(
    "  const raw = typeof body.assignee === 'string' ? body.assignee.replace(/\\t/g, ' ') : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.7"] = [("line breaks in the name become spaces", [asg(
    "  const raw = typeof body.assignee === 'string' ? body.assignee.replace(/[\\r\\n]/g, ' ') : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.8"] = [("other C0 controls in the name become spaces", [asg(
    "  const raw = typeof body.assignee === 'string' ? body.assignee.replace(/[\\u0000-\\u0008\\u000b\\u000c\\u000e-\\u001f]/g, ' ') : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.9"] = [("DEL in the name becomes a space", [asg(
    "  const raw = typeof body.assignee === 'string' ? body.assignee.replace(/\\u007f/g, ' ') : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.10"] = [("a numeric assignee is converted to text", [asg(
    "  const raw = typeof body.assignee === 'number' ? String(body.assignee) : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.11"] = [("a boolean assignee is converted to text", [asg(
    "  const raw = typeof body.assignee === 'boolean' ? String(body.assignee) : body.assignee;\n  return assignee(raw);\n")])]
V["R-4.12"] = [("the refusal message no longer names assignee", [asg(
    "  try {\n    return assignee(body.assignee);\n  } catch (error) {\n    if (error instanceof InvalidError) throw new InvalidError('invalid agent name');\n    throw error;\n  }\n")])]

# ---------------- R-5 ----------------
OLD_COND = "    if (!isActive(ticket.status)) {\n      throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer be assigned`);\n"
def cond(c):
    return (ST, OLD_COND, OLD_COND.replace("if (!isActive(ticket.status))", c))

V["R-5.1"] = [("open tickets are refused", [cond("if (!isActive(ticket.status) || ticket.status === 'open')")])]
V["R-5.2"] = [("in_progress tickets are refused", [cond("if (!isActive(ticket.status) || ticket.status === 'in_progress')")])]
V["R-5.3"] = [("unassigning an in_progress ticket is refused", [after_guard(
    "    if (assignee === null && ticket.status === 'in_progress') throw new ConflictError(`ticket ${id} is in progress`);\n")])]
V["R-5.4"] = [("resolved tickets accept assignment", [cond("if (!isActive(ticket.status) && ticket.status !== 'resolved')")])]
V["R-5.5"] = [("closed tickets accept assignment", [cond("if (!isActive(ticket.status) && ticket.status !== 'closed')")])]
V["R-5.6"] = [("the assignee is set before the refusal", [guard_replace(
    "    if (!isActive(ticket.status)) {\n      ticket.assignee = assignee;\n      throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer be assigned`);\n    }\n")])]
V["R-5.7"] = [("an audit entry is appended before the refusal", [guard_replace(
    "    if (!isActive(ticket.status)) {\n"
    "      this.audit.append({ ticket: id, action: 'ticket.assigned', actor, at: this.now(), changes: { assignee: { from: ticket.assignee, to: assignee } } });\n"
    "      throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer be assigned`);\n    }\n")])]
V["R-5.8"] = [("a notice is enqueued before the refusal", [guard_replace(
    "    if (!isActive(ticket.status)) {\n"
    "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, this.now(), `ticket.assigned:${ticket.id}:${assignee}`);\n"
    "      throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer be assigned`);\n    }\n")])]
V["R-5.9"] = [("unassigning a non-active ticket is allowed", [cond("if (!isActive(ticket.status) && assignee !== null)")])]

# ---------------- R-6 ----------------
V["R-6.1"] = [("assigning the current agent conflicts", [after_guard(
    "    if (assignee !== null && ticket.assignee === assignee) throw new ConflictError(`ticket ${id} is already assigned to ${assignee}`);\n")])]
V["R-6.2"] = [("a same-agent assignment appends an audit entry", [after_guard(
    "    if (assignee !== null && ticket.assignee === assignee) {\n"
    "      this.audit.append({ ticket: id, action: 'ticket.assigned', actor, at: this.now(), changes: { assignee: { from: assignee, to: assignee } } });\n    }\n")])]
V["R-6.3"] = [("a same-agent assignment enqueues a notice", [after_guard(
    "    if (assignee !== null && ticket.assignee === assignee) {\n"
    "      this.notify(ticket, 'ticket.assigned', assignee, this.now(), `ticket.assigned:${ticket.id}:${assignee}:again`);\n    }\n")])]
V["R-6.4"] = [("a same-agent assignment moves updated", [after_guard(
    "    if (assignee !== null && ticket.assignee === assignee) ticket.updated = this.now();\n")])]
V["R-6.5"] = [("unassigning an unassigned ticket appends an audit entry", [after_guard(
    "    if (assignee === null && ticket.assignee === null) {\n"
    "      this.audit.append({ ticket: id, action: 'ticket.assigned', actor, at: this.now(), changes: { assignee: { from: null, to: null } } });\n    }\n")])]
V["R-6.6"] = [("unassigning an unassigned ticket moves updated", [after_guard(
    "    if (assignee === null && ticket.assignee === null) ticket.updated = this.now();\n")])]
V["R-6.7"] = [("the whitespace-padded name of the current agent counts as a change", [(APP, PUT_OLD,
    "    const raw = await body(req);\n"
    "    const assignee = validate.assignment(raw);\n"
    "    if (typeof raw.assignee === 'string' && raw.assignee !== assignee && store.get(params.id).assignee === assignee) {\n"
    "      store.assign(params.id, null, actorOf(req));\n"
    "    }\n"
    "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n")])]

# ---------------- R-7 ----------------
V["R-7.1"] = [("the audit action is ticket.updated", [(ST, APPLY, APPLY.replace("'ticket.assigned', changes, actor", "'ticket.updated', changes, actor"))])]
V["R-7.2"] = [("two audit entries per assignment", [apply_replace(
    "    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
    "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);\n"
    "      this.audit.append({ ticket: ticket.id, action: 'ticket.assigned', actor, at, changes });\n"
    "    });\n")])]
def logged(expr):
    return (ST, AUDIT_APPEND,
            "    const logged = " + expr + ";\n    this.audit.append({ ticket: ticket.id, action, actor, at, changes: logged });\n")
V["R-7.3"] = [("an unset previous assignee is recorded as an empty string", [logged(
    "action === 'ticket.assigned' && changes.assignee && changes.assignee.from === null ? { assignee: { from: '', to: changes.assignee.to } } : changes")])]
V["R-7.4"] = [("an unassignment loses the previous name in the audit entry", [logged(
    "action === 'ticket.assigned' && changes.assignee && changes.assignee.to === null ? { assignee: { from: null, to: null } } : changes")])]
V["R-7.5"] = [("a reassignment loses the previous name in the audit entry", [logged(
    "action === 'ticket.assigned' && changes.assignee && changes.assignee.from !== null && changes.assignee.to !== null ? { assignee: { from: null, to: changes.assignee.to } } : changes")])]
V["R-7.6"] = [("the assignment is audited as system", [(ST, APPLY, APPLY.replace("'ticket.assigned', changes, actor", "'ticket.assigned', changes, 'system'"))])]
V["R-7.7"] = [("a request without X-Actor is audited as anonymous", [(APP, PUT_OLD,
    "    const assignee = validate.assignment(await body(req));\n"
    "    const actor = actorOf(req) === 'system' ? 'anonymous' : actorOf(req);\n"
    "    return { status: 200, body: store.assign(params.id, assignee, actor) };\n")])]
V["R-7.8"] = [("the audit entry is stamped with the ticket's creation time", [(ST, AUDIT_APPEND,
    "    this.audit.append({ ticket: ticket.id, action, actor, at: action === 'ticket.assigned' ? ticket.created : at, changes });\n")])]
HIST_OLD = "    return this.audit.forTicket(id).map((entry) => ({ ...entry, changes: { ...entry.changes } }));\n"
V["R-7.9"] = [("a history containing an assignment is returned newest first", [(ST, HIST_OLD,
    "    const entries = this.audit.forTicket(id).map((entry) => ({ ...entry, changes: { ...entry.changes } }));\n"
    "    return entries.some((entry) => entry.action === 'ticket.assigned') ? entries.reverse() : entries;\n")])]

# ---------------- R-8 ----------------
V["R-8.1"] = [("the notice has type ticket.created", [apply_replace(APPLY.replace("this.notify(ticket, 'ticket.assigned', assignee", "this.notify(ticket, 'ticket.created', assignee"))])]
V["R-8.2"] = [("the notice is addressed to the requester", [apply_replace(APPLY.replace("this.notify(ticket, 'ticket.assigned', assignee", "this.notify(ticket, 'ticket.assigned', ticket.requester"))])]
NOTIFY_DEF = "    return this.outbox.enqueue({ key, type, to, ticket: ticket.id, data: { title: ticket.title } }, new Date(at));\n"
V["R-8.3"] = [("the assignment notice carries no title", [(ST, NOTIFY_DEF,
    "    return this.outbox.enqueue({ key, type, to, ticket: ticket.id, data: { title: type === 'ticket.assigned' ? '' : ticket.title } }, new Date(at));\n")])]
V["R-8.4"] = [("the dedupe key does not distinguish the agent", [apply_replace(APPLY.replace("`ticket.assigned:${ticket.id}:${assignee}`", "`ticket.assigned:${ticket.id}`"))])]
V["R-8.5"] = [("every assignment gets a unique key", [apply_replace(APPLY.replace("`ticket.assigned:${ticket.id}:${assignee}`", "`ticket.assigned:${ticket.id}:${assignee}:${this.outbox.nextId}`"))])]
V["R-8.6"] = [("a return to an agent with a pending notice changes the ticket without an audit entry", [(ST, APPLY,
    "    if (assignee !== null && ticket.assignee !== assignee && this.outbox.pendingWithKey(`ticket.assigned:${ticket.id}:${assignee}`)) {\n"
    "      ticket.assignee = assignee;\n      ticket.updated = this.now();\n      this.save();\n      return { ...ticket };\n    }\n" + APPLY)])]
V["R-8.7"] = [("the delivered line names type ticket.created", [(NOT,
    "        type: event.type,\n", "        type: event.type === 'ticket.assigned' ? 'ticket.created' : event.type,\n")])]
V["R-8.8"] = [("an assignment notice is appended twice", [(NOT,
    "      if (file) fs.appendFileSync(file, `${JSON.stringify(line)}\\n`);\n      else delivered.push(line);\n",
    "      if (file) {\n        fs.appendFileSync(file, `${JSON.stringify(line)}\\n`);\n"
    "        if (event.type === 'ticket.assigned') fs.appendFileSync(file, `${JSON.stringify(line)}\\n`);\n      } else delivered.push(line);\n")])]
V["R-8.9"] = [("unassigning enqueues a notice for the previous agent", [apply_replace(
    "    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
    "      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);\n"
    "      else if (changes.assignee) this.notify(ticket, 'ticket.assigned', changes.assignee.from, at, `ticket.assigned:${ticket.id}:${changes.assignee.from}:unassigned`);\n"
    "    });\n")])]
V["R-8.10"] = [("a same-agent assignment enqueues a notice under the normal key", [after_guard(
    "    if (assignee !== null && ticket.assignee === assignee) {\n"
    "      this.notify(ticket, 'ticket.assigned', assignee, this.now(), `ticket.assigned:${ticket.id}:${assignee}`);\n    }\n")])]
V["R-8.12"] = [("the subject does not name the ticket", [(TPL,
    "    subject: `[${event.ticket}] Assigned to you`,\n", "    subject: 'Assigned to you',\n")])]
V["R-8.13"] = [("the body does not name the ticket", [(TPL,
    "    body: `Ticket ${event.ticket} \"${event.data.title}\" was assigned to you.`,\n", "    body: 'You have a new assignment.',\n")])]
V["R-8.14"] = [("a failed assignment delivery is recorded as sent", [(WRK,
    "        } catch (error) {\n          const after = store.recordDelivery(event.id, error);\n",
    "        } catch (error) {\n          if (event.type === 'ticket.assigned') {\n            store.recordDelivery(event.id);\n            report.sent += 1;\n            continue;\n          }\n          const after = store.recordDelivery(event.id, error);\n")])]
V["R-8.15"] = [("a key that was ever used is never reused for an assignment notice", [apply_replace(
    "    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
    "      const key = `ticket.assigned:${ticket.id}:${assignee}`;\n"
    "      if (assignee !== null && !this.outbox.events.some((event) => event.key === key)) this.notify(ticket, 'ticket.assigned', assignee, at, key);\n"
    "    });\n")])]

# ---------------- R-9 ----------------
V["R-9.1"] = [("an assignee filter with a name is ignored", [(QRY, MF,
    "  const given = Object.entries(filters).filter(([field, value]) => value !== undefined && !(field === 'assignee' && value !== null));\n  return given.every(([field, value]) => ticket[field] === value);\n")])]
V["R-9.2"] = [("the empty assignee filter is ignored", [(QRY, MF,
    "  const given = Object.entries(filters).filter(([field, value]) => value !== undefined && !(field === 'assignee' && value === null));\n  return given.every(([field, value]) => ticket[field] === value);\n")])]
V["R-9.3"] = [("a name filter that matches nothing falls back to the unfiltered page", [(ST,
    "    const page = paginate(matching, { limit, after, compare: compareIds });\n",
    "    const shown = matching.length === 0 && filters.assignee ? [...this.tickets.values()].sort((a, b) => compareIds(a.id, b.id)) : matching;\n"
    "    const page = paginate(shown, { limit, after, compare: compareIds });\n")])]
V["R-9.4"] = [("status and priority combine with OR", [(QRY, MF,
    "  const given = Object.entries(filters).filter(([, value]) => value !== undefined);\n"
    "  const sp = given.filter(([field]) => field !== 'assignee');\n"
    "  const a = given.filter(([field]) => field === 'assignee');\n"
    "  return (sp.length === 0 || sp.some(([field, value]) => ticket[field] === value)) && a.every(([field, value]) => ticket[field] === value);\n")])]
V["R-9.5"] = [("assignee combines with the other filters by OR", [(QRY, MF,
    "  const given = Object.entries(filters).filter(([, value]) => value !== undefined);\n"
    "  const a = given.filter(([field]) => field === 'assignee');\n"
    "  const others = given.filter(([field]) => field !== 'assignee');\n"
    "  if (a.length && others.length) return ticket.assignee === a[0][1] || others.every(([field, value]) => ticket[field] === value);\n"
    "  return given.every(([field, value]) => ticket[field] === value);\n")])]
V["R-9.6"] = [("priority is dropped when an assignee filter is given", [(QRY, MF,
    "  const given = Object.entries(filters).filter(([field, value]) => value !== undefined && !(field === 'priority' && filters.assignee !== undefined));\n  return given.every(([field, value]) => ticket[field] === value);\n")])]
V["R-9.8"] = [("a filtered page with a next cursor drops its last item", [(ST,
    "    return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };\n",
    "    if (filters.assignee !== undefined && page.next && page.items.length > 1) page.items.pop();\n"
    "    return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };\n")])]
FILT = "    filters.assignee = value === '' ? null : agentName(value);\n"
V["R-9.9"] = [("a whitespace-only assignee filter selects the unassigned tickets", [(QRY, FILT,
    "    filters.assignee = value.trim() === '' ? null : agentName(value);\n")])]
V["R-9.10"] = [("an over-long assignee filter is accepted", [(QRY, FILT,
    "    filters.assignee = value === '' ? null : (value.length > 64 ? value : agentName(value));\n")])]
V["R-9.11"] = [("a control character in the assignee filter is accepted", [(QRY, FILT,
    "    filters.assignee = value === '' ? null : (/[\\u0000-\\u001f\\u007f]/.test(value) ? value : agentName(value));\n")])]
V["R-9.12"] = [("a 64-character assignee filter is refused", [(QRY, FILT,
    "    filters.assignee = value === '' ? null : agentName(value.length === 64 ? `${value}x` : value);\n")])]

# ---------------- R-10 ----------------
ASG_COL = "  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee ?? '-' },\n"
V["R-10.1"] = [("the ASSIGNEE column always shows -", [(FMT, ASG_COL, "  { title: 'ASSIGNEE', value: () => '-' },\n")])]
V["R-10.2"] = [("an unassigned ticket shows an empty ASSIGNEE cell", [(FMT, ASG_COL, "  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee ?? '' },\n")])]
RAWL = "  return RAW_COLUMNS.map((column) => ticket[column]).join('\\t');\n"
V["R-10.3"] = [("the fifth raw cell says assigned instead of the name", [(FMT, RAWL,
    "  return RAW_COLUMNS.map((column) => (column === 'assignee' && ticket.assignee !== null ? 'assigned' : ticket[column])).join('\\t');\n")])]
V["R-10.4"] = [("an unassigned ticket prints - in the fifth raw cell", [(FMT, RAWL,
    "  return RAW_COLUMNS.map((column) => (column === 'assignee' && ticket.assignee === null ? '-' : ticket[column])).join('\\t');\n")])]
V["R-10.5"] = [("raw columns 1 and 4 are swapped", [(FMT,
    "const RAW_COLUMNS = Object.freeze(['id', 'status', 'priority', 'title', 'assignee']);\n",
    "const RAW_COLUMNS = Object.freeze(['title', 'status', 'priority', 'id', 'assignee']);\n")])]
V["R-10.6"] = [("the weekly report skips lines that carry a fifth column", [(WEEKLY,
    "    const columns = line.split('\\t');\n", "    const columns = line.split('\\t');\n    if (columns[4]) continue;\n")])]
V["R-10.7"] = [("show no longer lists assignee", [(FMT,
    "  const fields = ['status', 'priority', 'assignee', 'requester', 'created', 'updated'];\n",
    "  const fields = ['status', 'priority', 'requester', 'created', 'updated'];\n")])]
