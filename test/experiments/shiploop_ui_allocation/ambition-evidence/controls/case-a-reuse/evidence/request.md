# Controlled request — A: reuse and enrich

Plan **W1 only** for Field Notes: add a compact account-scoped export-activity
companion to the existing narrow notes experience. It should make queued,
running, complete, and failed export changes feel intentional and easy to
understand without interrupting a person who is selecting, reading, or editing a
note.

The desired experience is rich but truthful: a clear at-a-glance activity
surface, state-specific hierarchy, a useful focus-preserving way to refresh a
failed/stale view, and restrained motion that highlights a real pending,
accepted, or remotely changed state. Do not invent percentage progress, elapsed
time, delivery, or success that the supplied status contract does not expose.
The component must retain failure information and a next action beyond a
transient toast, coalesce repeated unchanged updates, and offer an accessible
reduced-motion alternative. Account changes and late reads must not show one
account's data to another.

The scope remains a read-only observer of the supplied GET status contract. It
does not request an export, download a result, create storage, add a server or
socket, or alter Field Notes' existing list/detail/edit/save/cancel/back
journeys. Persistent drafts are W2 and remain separately blocked.
