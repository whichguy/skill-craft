"""Wording variants for the interaction-design block's lifecycle paragraph (round 2)."""
LIFE_SHIPPED_START = "State and information lifecycle. For each piece of state the request involves,"

V1_EXTRA = """Choose the simplest placement that meets the request: a single-user game or tool
with no shared or lasting state runs entirely in the client. Add server state,
identity, a store or a live channel only for a requirement that needs it, and use
the runtime's native storage, identity, cache, workflow and notification services
before building your own. For each hop, pick the lightest channel that meets the
freshness the request states: request/response; polling at a stated interval;
email or platform notification for changes hours apart; server-sent events,
WebSockets or platform push only when seconds matter. After a push, poll gap or
reconnect, read the authoritative state back. Cache only derived data, in the
runtime's cache, with an expiry that matches the staleness the request allows.
State each channel's and cache's cost against the runtime's quotas.
"""
OLD_READ = "who may read it (hidden information never reaches a client that must not\nsee it);"
NEW_READ = ("who may read it (information one user must not see, such as an opponent's\n"
            "fleet or another person's record, stays off that user's client; information a\n"
            "lone user could only misuse against themselves may stay on their client);")
FLOOR = """Simplicity removes machinery, never safeguards: at every placement, keep the
personal-data handling above, a server-side check on every action by a caller the
product does not control, and validation and abuse limits on anonymous input.
"""
FLOOR5 = """Simplicity removes machinery, never safeguards: at every placement, keep the
personal-data handling above, a server-side check on every action by a caller the
product does not control, validation and abuse limits on anonymous input, and a
record of every background or asynchronous failure that reaches whoever must act.
"""

V3 = """Architecture decisions. Decide and state each of these in proportion to the request;
a line may be one sentence, and a choice the request leaves open goes to the user
with the default you would take and what it rules out.
1. Placement. Choose the lowest rung that meets the request: everything in one
   client; a client with one small server endpoint for the shared or trusted part;
   shared server state that others see on their next visit or by notification;
   shared server state with a live channel; scheduled or triggered jobs with no
   client; or server state open to anonymous callers. Name what would move it up a
   rung, without building it.
2. People and trust. Who uses it and how the runtime identifies them; sign-in only
   where users must be told apart. What one user must not see or do to another's
   data, the public's or a third party's: that stays off their client and is
   checked on the server. What a lone user could only misuse against themselves may
   stay on their own client.
3. State. For each piece: its owner and the native store that holds it, and why that
   store fits; who may read it; how simultaneous changes resolve; what survives a
   reload, disconnect or crash and how a client resynchronizes; what ends it and
   what removes it.
4. Channels. For each hop, the lightest channel that meets the stated freshness:
   request/response; refresh on the next visit; email or platform notification for
   changes hours apart; polling at a stated interval; server-sent events,
   WebSockets or platform push only when seconds matter. After a push, gap or
   reconnect, read authoritative state back. Retries and duplicate deliveries must
   not apply an action twice; where connectivity drops, queue locally and replay
   with a conflict rule. State each channel's cost against the runtime's quotas.
5. Caching. Only derived or expensive data, in the runtime's cache or a
   precomputed summary, with an expiry that matches the staleness the request
   allows; never the authority; none where it does not pay off.
6. Safeguards, at every placement; simplicity never removes them. Personal data:
   what is held or sent to a third party, where it is shown, stored and logged, how
   long it is kept and how it is removed. Secrets stay in the runtime's secret
   facility and never reach a client. Every action by a caller the product does not
   control is checked on the server; anonymous input is validated and rate- or
   abuse-limited.
7. Leverage. Map each decision to what the runtime and the project's own layers
   already offer, from their documentation, configuration and code; build new only
   for an evidenced gap, and name the quotas and limits the design meets.
"""

V4 = """Architecture decisions, each stated in proportion to the request (one sentence can
do); open choices go to the user with your default.
1. Placement: the lowest rung that meets the request (one client; client plus a
   small endpoint for the shared part; shared server state seen on next visit or by
   notification; shared state with a live channel; scheduled jobs; anonymous
   callers). Name what would move it up; do not build it.
2. Trust: sign-in only where users must be told apart. What one user must not see or
   do to another's, the public's or a third party's data stays off their client and
   is checked on the server; a lone user's own state may stay on their client.
3. State: owner and native store, readers, concurrency rule, recovery after reload
   or disconnect, end of life and removal.
4. Channels: the lightest that meets the stated freshness (request/response, next
   visit, notification, polling, then push only for seconds); read state back after
   a push or gap; no double-applied retries; offline queue where connectivity drops;
   cost against quotas.
5. Caching: derived data only, native cache, expiry matched to allowed staleness,
   never the authority.
6. Safeguards at every placement: personal data held or sent to third parties,
   where shown, stored and logged, kept how long, removed how; secrets in the
   runtime's secret store, never on a client; server checks on callers you do not
   control; validation and abuse limits on anonymous input.
7. Leverage: native runtime and project-layer services first; new only for an
   evidenced gap; name the quotas met.
"""

V6 = V4.replace(
    "   callers). Name what would move it up; do not build it.\n",
    "   callers). Name what would move it up; do not build it. A lower rung removes\n"
    "   machinery, never the safeguards in item 6.\n").replace(
    "3. State: owner and native store, readers, concurrency rule, recovery after reload\n   or disconnect, end of life and removal.\n",
    "3. State: owner and native store, readers, concurrency rule, recovery after reload\n"
    "   or disconnect, and what ends it (finished, abandoned, expired) and removes it.\n").replace(
    "6. Safeguards at every placement: personal data held or sent to third parties,\n"
    "   where shown, stored and logged, kept how long, removed how; secrets in the\n"
    "   runtime's secret store, never on a client; server checks on callers you do not\n"
    "   control; validation and abuse limits on anonymous input.\n",
    "6. Safeguards at every placement, never reduced for simplicity: personal data held\n"
    "   or sent to third parties, where it is shown, stored and logged, how long it is\n"
    "   kept and how it is removed; secrets in the runtime's secret store, never on a\n"
    "   client; server checks on every action by a caller you do not control;\n"
    "   validation and abuse limits on anonymous input; background failures recorded\n"
    "   where someone who can act sees them.\n")
assert V6 != V4 and V6.count("never the safeguards") == 1 and "background failures" in V6 and "abandoned, expired" in V6

def build(shipped_block):
    """Return {variant: interaction-design block}."""
    i = shipped_block.index(LIFE_SHIPPED_START)
    head, life = shipped_block[:i], shipped_block[i:]
    assert OLD_READ in life
    v1 = head + life.replace(OLD_READ, NEW_READ).rstrip("\n") + "\n" + V1_EXTRA
    v2 = head + life.replace(OLD_READ, NEW_READ).rstrip("\n") + "\n" + V1_EXTRA.replace(
        "before building your own.", "before building your own.\n" + FLOOR.rstrip("\n"), 1)
    v5 = head + life.replace(OLD_READ, NEW_READ).rstrip("\n") + "\n" + V1_EXTRA.replace(
        "before building your own.", "before building your own.\n" + FLOOR5.rstrip("\n"), 1)
    return {"shipped": shipped_block, "v1": v1, "v2": v2, "v3": head + V3, "v4": head + V4, "v5": v5, "v6": head + V6}

if __name__ == "__main__":
    import sys
    b = build(open(sys.argv[1]).read())
    for k, v in b.items(): print(k, len(v.split()), "words")
