# Passes

## Pass 1 - the ground
Added U-1 to U-6 (valid import, preparing a file, row problems, unusable file, non-admin, invited person) and C-1 to C-31: columns, header rules, CSV syntax, encoding, per-field validation, duplicates, atomic outcome, record numbering, error content, and the two lists of refusal reasons. Found nothing on: further user fields (split names, phone, groups) - deliberately limited to email, name, role.

## Pass 2 - what each sentence takes for granted
"Admins": who counts (C-32 to C-36). "Upload a CSV": one file, judged by content, limits, rate (C-50 to C-56). "Bulk-create users": what a created user is, where it lives, its credentials, invitations and activation (C-37 to C-47, C-57 to C-69). What the admin sees after each outcome, error display caps and safe display (C-41 to C-49). Found nothing on: formats other than CSV (an .xlsx is refused as binary, C-11).

## Pass 3 - the people who run it
Added U-7 to U-14 and C-70 to C-95: parity with the one-user form, undo, user limit, the off switch (default off), effect without restart, email-not-configured block, limit settings and their ranges, import history and details, the record and its outcomes, internal-error handling, file contents not retained, time bound, logs, monitoring, retention, existing data unchanged, switch-off, rollback, and the exact list of operator controls with what is deliberately not configurable.

## Pass 4 - where the parts meet
Added U-15, U-16 and C-96 to C-111. Parts walked: import vs import, import vs the one-user form, import vs double submission, undo vs acceptance, undo vs resend, resend vs resend, acceptance vs acceptance, rate limit vs concurrency, switch and limits changing mid-import, admin demotion mid-import, connection loss before and after the file arrived, restart mid-import, invitation status transitions (listed in full, C-104), users that no longer exist shown in details (C-111). Found nothing on: an undo racing a second undo beyond C-75; two admins viewing the same details (the page is not live, nothing to specify).

## Pass 5 - the runtime's own rules
Runtime named: a web application behind an HTTP proxy, with a database and an outside mail system. Added C-112 to C-120: HTTPS only, cross-site request refusal, request-body limit below the proxy's (figure unconfirmed), invitation pacing and the 60-minute / 6-hour bounds (mail system's own rate unconfirmed), retry spacing, sender address, no caching of personal data, keyboard and screen-reader use. The 30-second synchronous bound (C-86) is stated with the platform timeout marked unconfirmed. Found nothing on: browser limits on file inputs, database transaction size (1,000 to 10,000 inserts is within any ordinary limit).

## Pass 6 - what must not change, what must never happen
Added C-121 to C-124: records visible only within the organisation, an import never updates an existing user, undo removes only what the import created, no existing permission or flow changes. Already covered earlier and not repeated: no partial creation (C-25, C-84, C-110), no duplicate address (C-96 to C-100), no invitation for an uncreated user (C-58), no personal data in logs (C-45, C-85, C-87, C-89), same rules on both creation paths (C-70).

## Pass 7 - grind: reading as the one who builds it
Found and fixed: zero-byte file and blank-first-record had no clause (C-125, C-126); malformed quoting was only partly defined (C-12) and a quote inside an unquoted field was undecided (C-131); NUL versus non-UTF-8 precedence (C-10, C-11); empty header cell (C-5); what counts toward the hourly limit (C-56); what a "send" is for the 3-attempt rule (C-62); the 10,000-row ceiling had to meet the 30-second bound (C-86); undo only for succeeded imports (C-127); pending users never expire (C-128); import reference properties (C-129); role counts in the result (C-130); email states its expiry (C-132); record number per created user needed by C-111 (C-83).

## Pass 8 - grind: choices and "and"
Separated every choice that was sharing a clause with a request-derived or implied behaviour (deleted users' addresses C-135, default-off C-136, no record for early refusals C-134, undo permission now flagged as a choice in C-71) and split clauses that were two behaviours (C-9 / C-142, C-41 / C-139, C-46 / C-137 / C-138, C-65 / C-140, C-68 / C-141). Added the empty-history case (C-133).

## Pass 9 - grind: dimensions and bounds
Checked every dimension clause lists its members (refusal reasons C-30 C-31, statuses C-61 C-104, outcomes and undo states C-83, operator controls C-95, fields C-38 C-83, states that make an admin not an admin C-32, states of an existing user C-24) and every bound has a number (254, 100, 1,000, 5 MiB, 10,000, 10 MiB, 30 per hour, 100 errors, 7 days, 3 attempts, 1 and 5 minutes, 60 seconds, 30 seconds, 60 minutes, 6 hours, 90 days, 12 characters, 255 characters). Found: duplicate-in-file rule vs invalid addresses (C-23), file names shown as plain text (C-47), size of the invitation bound at 10,000 users (C-115), and the password-reset path around the invitation (C-143).

## Pass 10 - the pass that added nothing
Read every use case against its clauses (each has its ordinary, edge and unhappy path, or says why not), every cross-reference against the clause it names (numbers run C-1 to C-143 and U-1 to U-16 with no gap, no reference beyond them), every Source against the rule that a choice lives in its own clause, and every Observable for something a person outside the code could see. Looked for: an unobservable Observable, a word with two readings, an unwritten number, a state with no end, a silent decision, a two-in-one clause. Found nothing a builder would otherwise have got wrong. Stopped here.
