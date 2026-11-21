# Passes

Context: the working directory held no code and no invoicing system, so nothing in the request could be checked against an existing product. Where the invoicing system's states, permissions or provider are unknown, the spec says so and decides (Source: choice). The "existing rules to keep" are therefore the invariants C-41, C-42, C-45, C-80 and C-81.

## Pass 1 — the ground
Added U-1..U-14 and C-1..C-44: ordinary reminder, partial payment, settle, operator on/off/pause, history, undelivered, first-time enablement with backlog, edits mid-sequence, several recipients, permission refusal, late/duplicate runs, non-production. Found nothing yet on: bounces, reopened invoices, provider failure, retries as separate cases (added in pass 2/3).

## Pass 2 — what each sentence takes for granted
"Set up" takes for granted a sender identity, settings, permissions: added C-45..C-48, C-64, C-65, C-79. "Unpaid invoices" takes for granted a definition of unpaid and a state list (C-2, C-3), a currency and amount format (C-49), recipients that exist and are valid (C-24, C-27, C-75, C-76), an invoice that still exists (C-56). "Automatic reminders" takes for granted an end to the sequence (C-7), a time of day (C-9) and a calendar (C-8). Added U-15..U-18 and C-49..C-57.

## Pass 3 — where the parts meet
Pairs walked: payment vs send (C-36), pause vs send (C-22, C-57), off vs evaluation under way (C-17), two evaluations at once (C-32), crash between send and record (C-50), due-date change vs sent steps (C-33, C-34), schedule change vs sent steps (C-35, C-78), reopen vs skipped steps (C-3, C-55), recipient added after send (C-54), two operators saving settings (C-85), partial recipient success (C-38), bounce after acceptance (C-52, C-53), provider unreachable vs retry count (C-82). Added C-50..C-58, C-77, C-78, C-82, C-83, C-85.

## Pass 4 — the runtime's own rules
No runtime or provider is named in the request. Clauses state the behaviour forced by the usual rules of scheduled jobs and mail delivery, with unconfirmed figures marked: scheduler may fire late/twice (C-32, C-39), maximum run time (C-63), provider rate limits and quotas (C-62), volume target (C-40), sender-domain verification before real mail (C-64), no real mail from non-production (C-43), credentials not exposed (C-65), daylight-saving days (C-9), invoice store unreadable (C-72). Unconfirmed figures: provider rate 10/s, 2-hour volume target, platform execution limit.

## Pass 5 — what must not change, what must never happen
Must not change: invoice data (C-41), invoicing operations (C-42), existing emails (C-80). Must never happen: a reminder after a recorded payment (C-36, C-57), a recipient getting a step twice (C-32), someone seeing history or addresses they may not (C-61, C-81), a sender fault suppressing recipients (C-77), data lost on settings change (C-46, C-73, C-85), a stop rule enforced in one send path and not another (C-57), another invoice's content in an email (C-86).

## Pass 6 — grind (whole spec read as the builder)
Found and fixed: C-3 vs reopened invoices (skip is not final), C-11 recording of expired steps when reminders were off, C-29 timing line defined by actual send date not nominal offset, C-39 so that the 60-minute bound on first attempt is stated, C-40 volume arithmetic (50,000 emails at 10/s fits 2 hours), C-64 half-clause removed, C-58 wording, C-35 vs out-of-order sending (C-78), recipients repeated or invalid (C-75, C-76), C-24 limit of 5 made precise. Added C-75..C-81.

## Pass 7 — grind
Found and fixed: clauses that were two (C-30 split into C-30 and C-86; C-37 split into C-37, C-82, C-83); C-20 contradicted C-17 on when "off" applies; C-38 had no outcome for unknown results (C-50); C-43 Observable had no value to look at; U-8 promised a list that C-60 could not show (recipient-result filter added); next-step reasons had no list (C-84); C-45 did not cover invoices that existed before the feature. Added C-82..C-86.

## Pass 8 — grind (the stopping pass)
Read every use case and every clause again, checking: clause-against-clause contradictions (C-17/C-20, C-38/C-58, C-3/C-55, C-24/C-76, C-53/C-76, C-33/C-78, C-9/C-39, C-40/C-62), each dimension named has its members (invoice states C-2/C-3, settings C-19, message parts C-28, controls and exclusions C-68, reasons C-71/C-84, history fields C-31, who sees what C-61), each bound has a number (schedule 1–10 offsets, -30..365, window 3 days, 60 minutes between attempts, 3 attempts, 5 recipients, 15-minute unknown, 100/254/1,000 characters, 24 months), each use case has an unhappy path (U-4, U-8, U-12, U-13, U-17), each piece of state has an end (steps end C-7, pause ends C-23, history ends C-44, evaluation and settings logs C-59, C-20), and that numbering has no gaps (U-1..U-18, C-1..C-86, checked by count). The only thing found was one contradiction (C-58 gave "failed" where C-38 allows "outcome unknown"), fixed in place; a re-read of the changed clause found nothing further. No further behaviour a builder would otherwise have got wrong was found in this pass.
