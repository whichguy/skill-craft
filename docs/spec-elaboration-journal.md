# Spec elaboration journal

Living journal of the side experiment on the prompt that turns a small, vague incoming request into a verbose
specification. Apparatus: `docs/experiments/spec-elaboration-20261120/`. Edit entries rather than delete them; a
claim that stops holding is marked superseded with the date and the reason.

## 1. Registration (2026-11-20, before any call)

**Why this exists.** Owner, 2026-11-20: a prompt that takes an incoming vague prompt — an action, maybe
environments — and elaborates it into a verbose specification, recursing to find what the request leaves
implicitly defined and how the interactions work, "iteratively grind[ing] through them, looking for nuance and
detail". The sample request is the owner's: a Grok bot in a Salesforce development org, with the bot's nature, its
operation, its async activities, its interface and its stored schema all to be defined from that one sentence. The
owner asked for Sonnet at high and GPT-6.2 Sol at medium as the drivers, for a few more sample requests beside the
Grok bot, and for test cases and per-iteration results to be retained so the prompt can be iterated repeatedly.
The stated intent is a small side experiment, reincorporated into ShipLoop afterwards.

**Where it sits beside work already running.** The ratchet pilot (branch `ratchet-pilot-b6eab2`, journal
`docs/ratchet-pilot-journal.md`, runs under `/Users/dadleet/e2e-runs/ratchet-pilot-20261120-b6eab2/`) registered
amendment 1 earlier the same day, commit e63747a3d: its spec stage became "a rich enrichment (use cases, implied
requirements)" from the owner's fifth message, which is the same thread of intent. That pilot measures the
enrichment *through the built product* — whether the resulting test suites catch more of 37 calibrated defects —
over four small code cases, and its runs were in flight when this experiment was registered. This experiment
measures the elaboration prompt *directly*, on the specification text, over requests that include a platform-shaped
one the pilot has no case for, at the two drivers the owner named here. They are complementary instruments on one
question; neither replaces the other, and this session did not touch the pilot's branch, worktree or runs.

**What is registered.** `docs/experiments/spec-elaboration-20261120/README.md` holds the design: two arms
(`A-single`, the ratchet enrich text as the control; `B-recursive`, six named passes with a stop rule), four frozen
one-sentence requests, 89 held-out nuances written before any run, the two drivers, the measurement (script counts
plus an Opus coverage verdict per nuance), and the readings R1 to R5 with their thresholds. Registration commit:
this one.

**Known limits of the instrument, stated up front.**
- The 89 held-out nuances are this session's own predictions of what matters, not an external ground truth. They
  are frozen and never edited after an arm's output is read, which keeps them honest, not authoritative.
- One call a cell. Every round-1 number is interim; a difference at R1's threshold needs a replicate.
- Subjects keep their built-in tool set, so a subject may search the web for a platform limit. That is realistic
  for the real stage, and `counts.json` records the tools each call used, so a coverage difference traceable to a
  lookup rather than to the prompt is visible rather than hidden.
- Both arms were written by this session, so the control is as strong as this session could make it (the state of
  the art in the repository), not as weak as it could make it. That is the honest form of the comparison, but it is
  not a blind one.
