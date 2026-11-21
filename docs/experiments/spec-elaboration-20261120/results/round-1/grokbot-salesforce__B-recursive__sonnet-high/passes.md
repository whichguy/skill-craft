# Passes

## Pass 1 — the ground
Added U-1..U-13 and C-1..C-42: the ordinary chat (open, send, answer, follow-up, new conversation), the stored-conversation edges (first time, list, paging, reopen, delete), the unhappy paths (empty, too long, not set up, off, timeout, 429, 5xx, 401/403, unreachable, empty answer, rate cap, full conversation) and the operator's work (key, model, instruction, limits, on/off, call log, retention, redeploy). Decided the reading of "Grok bot": a chat assistant in a Lightning tab backed by xAI's Grok API (not Einstein Bot, Agentforce, Slack or Messaging).
Found nothing on: access control, platform rules, concurrency (left to later passes).

## Pass 2 — what each sentence takes for granted
Asked of "Create a Grok bot in a Salesforce development org" and of each pass-1 clause what must already be true. Added: who may chat and who administers (two permission sets, C-43), credential access for chat users (C-44), how an administrator knows setup is done and proves it (status checklist C-45, test message C-46), one key for the org (C-47), what the hourly limit counts (C-48), what enforces retention (C-49), reasoning text, attachments, Unicode, language, empty states, paging a large transcript, the xAI notice, cut-off answers (C-50..C-58).
Found nothing on: the key's origin (an xAI account with billing is a fact about the world, not this product).

## Pass 3 — where the parts meet
Walked the pairs: send x send (two tabs, double click), send x delete, send x settings change, send x turn off, send x rate limit, send x conversation cap, send x cleanup, cleanup x bot off, cleanup x retention change, storage failure after a good answer, late answer after timeout, log failure x send. Added C-59..C-77.
Found nothing on: two different users meeting (they share nothing except the org's platform limits, covered in pass 4).

## Pass 4 — the runtime's own rules
Salesforce/Apex: no streaming (C-80), at most 120 s of callout wait per transaction so no retry (C-79) and the 5..100 s wait range (C-36), callouts only from the server (C-78), callout host authorisation shipped by the deploy (C-85), credential access via permission set (C-44), concurrent long-request limit (C-81, figure unconfirmed), 5 MB Developer Edition storage (C-71, C-40), 131,072-character long text (C-87), 6 MB heap driving paging (C-55), 10,000 DML rows driving chunked cleanup (C-75), tests cannot call out and need 75% coverage for production (C-82, C-83, C-84), secrets not carried by deployment (C-18, C-89), Lightning Web Security (C-86). Figures I am not sure of are marked unconfirmed inside the clause (concurrency threshold, xAI's context-length error wording, xAI's host and default model).
Found nothing on: daily limits on callouts (none apply to Apex callouts as far as known).

## Pass 5 — what must not change, what must never happen
Unchanged: nothing else in the org changes (C-88). Never: key leaks (C-31, C-89), data to anywhere but xAI (C-90), Salesforce data or identity sent (C-91), the bot acting on records (C-92), cross-user reads (C-93), forged messages (C-94), a rule enforced on the screen but not the server (C-95, C-98), public triggering (C-96, C-121), script injection from answers (C-97), raw errors shown (C-99), altered stored text (C-100), early deletion (C-101), guessed settings (C-102).
Found nothing on: an org-wide spend cap beyond the per-user hourly limit; left out deliberately, the request does not ask for it.

## Pass 6 — grind
Re-read from the top as the builder. Fixed: a clause that referred forward to a number that did not exist (C-9, C-26, C-36); several "X and Y" clauses split (C-34, C-37, C-40, C-41, C-64, C-66, C-68, C-96, C-103, C-104); a circular rule between the status checklist and cleanup scheduling (C-49); missing behaviours (other 4xx C-108, context too long C-111, turned-off reading C-109, no filtering C-110, purge actions C-112/C-113, timing C-114/C-115, log filter C-116, split-out clauses C-117..C-124); settings "in Setup" loosened to "in the org's user interface".

## Pass 7 — grind
Looked again for "and" clauses, for use cases without an unhappy path, for state without an end, and for ordinary things users rely on that nobody wrote down. Added C-125..C-132: continuing an opened conversation, nothing stored on failure, the deleted-conversation message, log retention, key whitespace, browser-to-Salesforce failure and session expiry, scrolling to the newest message, where administrators find their screens. Split the remaining double clauses (C-13, C-26, C-40, C-62, C-84, C-101). Checked every cross reference resolves and numbers C-1..C-132 and U-1..U-13 have no gaps.

## Pass 8 — grind
Read the whole specification from top to bottom. Found and fixed: a circular rule between the status checklist and the cleanup schedule (C-49 now keys off the key being entered); C-79 read as if duplicate submissions (C-69) broke it, so it now counts per submission; C-59 pointed at C-26 where C-126 is the clause about storage. Not a stopping pass, since it changed clauses a builder could have got wrong.

## Pass 9 — the stopping pass
Read the whole specification once more, top to bottom, looking for: an Observable nobody could observe, a word two readers would read differently, a number implied but not written, a use case with no unhappy path, a piece of state without an end (conversations, call log entries, request identifiers, hourly counts, settings and the scheduled job all end or are bounded), a decision made silently rather than marked as a choice, a clause that is really two, a clause whose Observable states more than its own requirement, a dangling reference or a gap in numbering. Found nothing a builder would otherwise have got wrong and changed no clause. Final state: U-1..U-13 and C-1..C-132 with no gaps.

## Left to the requester, decided as choices (each marked "choice" in the spec)
The reading of "Grok bot" (C-1), a hard 4,000-character message and 200-message conversation (C-17, C-29), 20 messages of history (C-7), 60 calls per hour (C-28, C-105), 30-day retention (C-40, C-106), 2,048 default maximum answer and 60 s default wait (C-35, C-36), internal users only (C-121), conversation-only bot with no CRM actions (C-92), plain text, no attachments (C-51), English only (C-53).
