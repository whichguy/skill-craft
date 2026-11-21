# Passes

## Pass 1 — the ground
Added U-1 to U-17 and C-1 to C-55: the ordinary chat (send, reply, follow-up), its edges (first time, new conversation, empty message, the 4,000-character limit, the 100-message and 50-conversation caps), the unhappy paths (Grok down, slow, rate-limited or rejecting the key; bot switched off; no key), the operator's work (deploy, key, settings, switch off, call log, clean-up), and privacy of conversations.
Found nothing on: surfaces other than the Lightning chat screen (decided in pass 2).

## Pass 2 — what each sentence takes for granted
"Create a Grok bot" took for granted: which Grok and which API (C-1), where it is found (C-2, C-56), that it needs no extra licence (C-57), that it is built from source into the org (C-58), that it speaks English (C-63), that times have a zone (C-64), that it is keyboard-operable (C-65), what an empty first-time screen shows (C-67), and that a failed list load is not shown as an empty list (C-66, U-18). "In a Salesforce development org" took for granted deployment, a README, and that an operator can enter a secret (C-58, C-62, C-38).
Found nothing on: a feature that reads Salesforce records for Grok. Left out deliberately (C-53).

## Pass 3 — where the parts meet
Walked pairs: two sends from two tabs (C-68), cap checks racing (C-69), send while the conversation is deleted (C-70), access revoked mid-session (C-72), switch off while a request runs (C-41), settings or key change while a request runs (C-83), two users at once (C-81), delete against the call log (C-23), clean-up against a send (C-70 covers a conversation that has gone).
Found nothing on: a user sending in two different conversations at once; the screen prevents it (C-5) and two tabs fall under C-68.

## Pass 4 — the runtime's own rules
Salesforce and xAI rules turned into behaviour: callout may not follow database writes in one request (C-73); 120 s cap for all callouts in one request, hence the 60 s wait (C-29); concurrent long-request limit, figure unconfirmed for development orgs (C-74); 6 MB callout size cap (C-75); unexpected governor errors (C-76); small data storage, figure unconfirmed (C-71, C-54); scheduled jobs are not deployable metadata (C-55); secrets cannot be deployed and are entered in Setup (C-38); outbound-credential access carried by the permission set (C-44); 75% coverage and no real callouts in tests (C-77); content-security rules for outside hosts (C-78); nothing org-specific baked in (C-82). The xAI parameter name for maximum reply length and the current model identifier are marked unconfirmed (C-6, C-34, C-35).
Found nothing on: API request-per-day limits (the chat screen's server calls are not API requests).

## Pass 5 — what must not change, and what must never happen
No existing product behaviour exists, so "must not change" became: deployment only adds (C-61), repeat deployment keeps data, settings and key (C-59), rollback keeps data (C-60). Never-lists: another user's text (C-49), the key leaking (C-8, C-47, C-31), a request twice (C-4, C-30), a half-stored turn (C-24), a rule enforced on the page but not the server (C-13, C-40, C-79), message content in the admin-wide log (C-47), data silently removed (C-21, C-85).
Found nothing on: any other existing rule to keep.

## Pass 6 — grind (whole read-through)
Added: C-84 (exactly what each permission set grants, the missing dimension list), C-85 (retention notice), C-86 (several refusal conditions at once). Fixed: forward references to clauses that did not exist yet (C-23, C-24, C-25, C-46), the "exactly those steps" README wording (C-62), the vague "about 70 seconds" (C-29 now 60 to 75), the call-log conversation field wording (C-45), the missing unhappy path in the first-time setup (U-10 now covers a mistyped key).

## Pass 7 — grind (second whole read-through)
Found and fixed: a wrong multiplier in the rationale of C-20 (100 is five times 20, not ten), whether a log row exists for a request the platform refuses (C-74) or for an unexpected error after Grok was called (C-76), a clause that was two (C-53, now one), and a vague phrase in a Source (C-54). Each of these was either a builder question or a misleading statement.

## Pass 8 — grind (final check; stop)
Re-read C-56 to C-86 and the cross-references, and walked every use case for a missing unhappy path, every limit for a number (4,000 chars; 20 context messages; 100 messages; 50 conversations; 80-character label; 60 s wait, 75 s ceiling; 255-character error summary; 4,000-character system prompt; 64 to 8,192 reply tokens, default 2,048; 30-day log and 90-day conversation retention; 75% coverage; 120 s, 6 MB and 10-request platform limits), every dimension for a full member list (settings, permission-set grants, log fields and outcomes, refusal conditions, failure kinds, README steps), and every Source for a stated reason. It added nothing a builder would otherwise have got wrong. This is the stopping pass.
Not done: an automated check that numbering has no gaps and every C-/U- reference resolves. The attempt to run one was not approved. Numbering was checked by count (18 use cases, 86 clauses, appended in order) and by reading.
