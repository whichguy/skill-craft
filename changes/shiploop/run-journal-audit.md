---
bump: patch
---
The run trace (`RUN/trace.jsonl`) and the Skill-call record (`RUN/skill-calls.jsonl`) are written as pure ASCII JSON lines
through one shared writer, and read by one shared reader that ends lines at `\n` only. A refusal, hook text or Skill
argument holding U+2028, U+2029 or U+0085 is no longer dropped by `shiploop trace`, and one holding a lone surrogate (an
undecodable file name) no longer loses its whole row. A command interrupted (exit 130) or crashed (exit 1) before it
answered is now traced with `crashed` and its reason instead of as a silent exit-2 refusal, so the trace, its page and the
refusal counts no longer count it as one. The Improve gate's "not enforced" line is shown but no longer counted as a Skill
call. The trace's field contract is documented in the status-display reference.
