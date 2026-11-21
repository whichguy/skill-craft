# Passes

## Pass 1 — the ground
Added U-1 to U-5 (first use, multi-turn, history management, failure and retry, usage limit) and C-1 to C-41: the end user's whole path (open, send, size limits, reply display, history sent to Grok, what is and is not sent, conversation list/open/continue/new/delete, per-user and per-conversation caps, the eleven failure categories and what the user is shown, retry, refusals, limits, the two notices).
Found nothing on: voice, attachments, images (deferred to pass 2 as an explicit exclusion).

## Pass 2 — what each sentence takes for granted
Sentence: "Create a Grok bot in a Salesforce development org." Words taken one at a time.
- "bot": what kind (C-42 not Einstein/Agentforce), what media (C-43 text only), what surfaces (C-46), what language (C-45), accessibility (C-47).
- "Grok": third party (C-40 notice, C-16 what it receives, C-17 where it goes, C-44 tools), its output (C-18, C-19, C-9 untrusted markup).
- "create ... in an org": someone must be allowed to see it (C-56, C-57, C-58), what gets stored (C-54, C-55), what happens while it is running when the user leaves (C-48 to C-53).
Own clauses re-asked: C-7 (what if the page is left: C-48, C-49), C-14 (what if the window cuts a pair: C-59; what if a message failed: C-15), C-11 (enforced where: C-38 and C-52).
Found nothing on: the "development org" itself and the operator side (deferred to pass 3), and platform limits (pass 5).

## Pass 3 — the people who run it
Added U-6 to U-14 and C-60 to C-114. Walked: first install (C-60 to C-64), connect and know it worked (C-65 to C-70), who may administer (C-71, C-72), configure and see it take effect (C-73 to C-87, every control with its default and range), turn off for everyone (C-88, C-89), for one user (C-90, C-91), watch and find the one failure (C-94 to C-103), look into a complaint (C-92), carry on with existing data and undo (C-110, C-113), bounded data (C-104 to C-111), go back or remove (C-112, C-114).
Found nothing on: a "turn off for one case" other than per user (a per-conversation off is not something an operator needs: they delete it).

## Pass 4 — where the parts meet
Parts listed: send, Retry, delete (user), delete (administrator), cleanup (scheduled and manual), settings save, key change, Enabled switch, permission removal, Test connection, two tabs, the limits, the log. Pairs walked: two sends in one conversation (C-115), sends in two conversations (C-116), limits under simultaneous sends (C-117), Retry arriving after later messages (C-118), delete under an in-flight reply (C-119), scheduled against manual cleanup (C-120), two administrators saving (C-121), permission removed during a call (C-122), repeated Test press (C-123), two refusals at once (C-124), log against limits (C-125), log write failing (C-126). Interactions already covered by earlier clauses were checked and left: Enabled switched off in flight (C-89), settings changed in flight (C-85), double Send (C-52).
Found nothing on: key replaced during a call (the call finishes with the key it began with, and a rejection is a normal "Key rejected" failure that C-33 retries); a redeploy during a call (the call fails in an existing category or completes).

## Pass 5 — the runtime's own rules
Runtime: Salesforce (Apex, Lightning Web Components, Named/External Credentials, metadata deploy), calling xAI's chat completions API. Rules turned into behaviour: callout time cap 120 s per transaction (C-80, C-34); no callout after uncommitted writes (C-32 reason); no streaming from Apex (C-144); 6 MB synchronous response (C-78); 10,000 DML rows per transaction (C-106); 100 scheduled jobs (C-133); concurrency limit on long requests (C-127, figure marked unconfirmed); Recycle Bin 15 days (C-110); secrets not deployable (C-64, C-130(2)); credential principal needed by users (C-57); no real callouts in tests and 75% coverage (C-129); deploy is all-or-nothing (C-132); developer org 5 MB storage (C-111, figure marked unconfirmed); org prerequisites (C-131); no browser-side access to xAI (C-128); what must be true beyond a development org (C-130). xAI facts marked unconfirmed in their clauses: endpoint path (C-17), 403 meaning (C-29), temperature range (C-77), default model (C-75), credit-exhaustion status (C-131).
Found nothing on: API-request limits of the org (they cap inbound API calls, and the bot makes outbound callouts only).

## Pass 6 — what must not change, what must never happen
Added C-135 (deploy changes nothing existing), C-136 (no other records touched, no other data sent), C-137 (a reply causes nothing), C-138 (every server-side operation checks its caller, listed in full), C-139 and C-140 (what is stored, what is refused), C-141 (first-time summary). Never-lists already in place: C-16, C-17, C-31, C-56, C-65 and C-152, C-97, C-102, C-128.
Found nothing on: existing behaviour of the org that this feature must keep (the org has none of this feature before it; C-135 is the whole of it).

## Pass 7 — grind: one behaviour per clause, ambiguous words
Split clauses that joined two behaviours (C-9, C-10, C-17, C-23, C-30, C-38, C-49, C-62, C-65, C-69, C-107) into C-142 to C-152. Found and fixed a counting error: C-28 capped messages at 200 in a way that could leave no room for a reply; it now caps user messages at 100 (so the total never exceeds 200) and C-38 follows. Added C-153 (a state with no end: the in-flight block). Corrected cross-references (C-15, C-41, C-56 title) and removed an unrequested rule (discarding the typed text in C-24).

## Pass 8 — grind: whole-spec read from the top as the builder
Read every clause. Found: the summary lacked the refusals the log records (added to C-100); the removal command left the scheduled cleanup job unmentioned (C-112); a choice hidden in a parenthesis (cleanup deletes permanently) moved into its own clause (C-154); the Timed-out clock had no start (added to C-50); the word "administrator" meant two things and platform-wide data rights were silent (C-155).

## Pass 9 — grind: the stopping pass
Looked for: a clause whose Observable cannot be observed (none: the least direct are C-102, C-117 and C-128, each with a stated way to observe it); a word two readers would read differently (checked "in flight", "counted attempt", "administrator", "latest message", "completed message", all defined in a clause); a number the request implies and nobody wrote (every limit, range, default, timeout and size has its value; the unconfirmed ones say so in their clause); a use case with no unhappy path (each use case has one: U-1 C-6/C-29, U-2 C-28, U-3 C-26/C-53, U-4 C-29, U-5 C-38, U-6 C-132, U-7 C-68, U-8 C-90, U-9 C-84, U-10 C-88, U-11 C-126, U-12 C-133, U-13 C-66, U-14 C-129); a piece of state with no end (messages in flight C-50, conversations C-104, logs C-105, last-test result replaced by the next test C-70); a decision made without a Source: choice (none found: every default and every exclusion is a choice clause); a clause that is really two (none left). Numbering checked: U-1 to U-14 and C-1 to C-155 with no gaps and no references to numbers that do not exist.
This pass added nothing a builder would otherwise have got wrong. Stopped here.
