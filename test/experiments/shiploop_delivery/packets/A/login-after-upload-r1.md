# ShipLoop fresh-context interpretation packet

Variant: A
Scenario: login-after-upload
Independent repetition: 1 of 2

This is a synthetic, read-only interpretation exercise. Do not execute commands,
inspect an ambient repository, contact a target, create a ShipLoop run, or submit
a completion callback. The facts below are the entire durable context.

## Current ShipLoop assignment

Current node: `release-verify`
Action: `synthetic-a-login-after-upload-r1`

## Original request

Make the visual movement cue available on the private development page and verify it works.

## Durable facts

- A permitted private source synchronization was recorded as successful and the served artifact matches the candidate.
- The consumer check reaches a login boundary before the visual interaction can be exercised.
- No evidence shows that repeating the synchronization would change the login boundary.

## Available reference material

- RELEASE.md: successful source synchronization and artifact identity observation.
- CONSUMER-CHECK.md: access is blocked at login; no visual behavior observation exists.

## Response requested

Describe the next appropriate action, which facts require a user decision or
current evidence, which evidence is still needed, and whether this assignment
would end in `done`, `blocked`, or `repeat`. Do not claim an external effect.

## Current stage instructions

The script owns only this cursor, action identity, durable state, and graph
routing. You own repository review, judgment, planning, edits, test design,
commands, evidence, and whether work has converged. Follow the user’s scope
and permissions; do not infer permission to release, push, install, delete, or
change unrelated work.

Use this packet's Current node and Action for your assignment and callback;
the Last accepted transition describes earlier work, not the current action.

Inspect current repository and run context before relying on prior notes. Keep
the candidate and adjacent context explicitly scoped, preserve unrelated user
work, and treat a missing prerequisite, access, decision, or trustworthy check
as incomplete rather than success. Choose proportionate ways to carry out this
prompt; no exact prose layout, check-manifest schema, byte comparison, or
generic evidence string proves quality.

Return a concise result with `outcome` (`done`, `repeat`, or `blocked`) and a
`summary`; add `evidence_refs` when they help locate real evidence. Do not
supply a next stage. `repeat` asks for a new action at this same node; `blocked`
keeps this work incomplete until the host resumes it. Only `plan` may include
ordered `work_items` for all approved work. `plan-improve` may update that
ordered queue before execution begins. Only `carry-forward` may include ordered
future-only `work_items`.


Verify the actual relevant release and consumer/runtime boundary using current
target evidence. Confirm the observed behavior, version or identity where
available, and release-specific checks; distinguish unavailable evidence from
a passed check. If release was genuinely non-applicable, verify the applicable
final consumer boundary and retain that reason.
