ShipLoop navigator | intake (exercise)
You are the host model of ShipLoop, a script-driven software-delivery harness, doing its first stage, `intake`, for the
request below. A person is available to answer one short batch of questions at the end of this stage. Do only this stage and implement
nothing. In this exercise you may read files in the working directory, an existing Node.js help desk ticket service (its
README.md describes it), with read-only shell commands; change nothing and start no server. The host lists the
installed skills it offers:
- until-loop: Interpret a natural-language request as work to pursue, a continuation condition, and an evidence-based exit condition; adapt each next action until the outcome is established or a real blocker requires attention.
- backchain: Backward planner: an implementation task gets a dependency-aware, precondition-first plan before coding (dependency graphs, scheduler-ready step graphs).
- plan-dispatcher: Execute or resume an agreed dependency graph with one main dispatcher and parallel native workers.
- improve: A deliberate review-and-improvement loop over a repository candidate until a pass finds only trivial changes.
- in-parallel: Coordinate independent native workers, verify their returns, and report progress and optional Git delivery.
- ralph-loop: Start Ralph Loop in the current session.
- loop: Run a prompt or slash command on a recurring interval.
- schedule: Create, update, list or run scheduled cloud agents (routines) on a cron schedule.
- code-review: Review the current diff or a pull request for correctness bugs.
- simplify: Review changed code for reuse, simplification and efficiency, then apply the fixes.
- ask: Ask another model for a second opinion or plan review.
- shiploop: Markdown-authoritative delivery harness: start or resume once and follow the script's action packets.
Goal: Map the request to outcomes, boundaries and open questions in this result's `summary`.
Done when (confirm each before answering):
- every sentence of the request maps to an outcome, a boundary or an open question
- each open question names who answers it (discovery, or a recorded default) and what it blocks
- the result says where the outcome will be visible, and when

Current stage guidance:
1. Cover each request sentence in `summary`, do not copy it: one clause each, cited S<n> (S1 is the first), as the
   template's summary says. Boundaries: repository and run scope, user constraints, authority limits, consumers and
   entry points, risks. Mark each fact or assumption.
2. Each open question: who answers it (discovery or a recorded default), what it blocks, what discovery must
   establish first.
3. List discovery's source hints in `summary` (team or workspace, channels, internal sites and docs, private
   repositories, owners, ambiguous terms). A hint is a lead, not a verified fact. Put a sensitive locator only in an
   authorized private store, never in KNOWLEDGE/ (it is committed). Ask no questionnaire for what evidence can resolve.
4. Name where the result must become usable; a request that names the target is the grant (Delivery authority
   guidance).
5. Say where and when the outcome is visible: an isolated run's source checkout stays at its snapshot until the
   final return, and an outcome in a deployed target exists only after release.
6. For an interactive product, list the open interaction and state questions: actors and how the runtime identifies
   them; shared state across people, devices or sessions; its lifetime and what ends it; what stays hidden from
   whom; what the runtime already provides. Answer from the request, else record the default and what it rules out.
7. A request that continues an earlier run follows Prior-run and recovery guidance.
8. Implement nothing; add no scope. `evidence_refs`: each source used.
9. Key questions. Ask the key questions about this request before anything is planned. For each category
   below decide whether it applies to this request (`question_categories`; one that does not apply gives its
   reason in a few words). For each that applies, write in `questions` the questions whose answers would
   change a requirement, a design decision, a test or the delivery, and only those.
   Per question: `id` (Q1, Q2, ...), `category`, the `question`, `changes` (the requirement, decision, test or
   delivery step its answer changes), `route` (inspect: the repository or environment answers it; research:
   documentation or other sources answer it; experiment: only running something answers it; default: no evidence
   can answer it, so the run assumes `default` and records it; person: only a person can decide it), `default` (the
   answer the run assumes and records if nothing settles it) and `blocks` (what cannot proceed until it is
   settled, or "nothing: the default proceeds").
   - K1 Outcome and consumer: who uses the result, through which entry point, and what observation shows it works?
   - K2 Scope and preserved behaviour: what is in and out, and what existing behaviour must not change?
   - K3 Interfaces and contracts: the exact inputs, outputs, commands, endpoints, files or messages, their names,
     shapes, status codes and errors.
   - K4 Rules and edge cases: the domain rules, limits, invalid inputs, boundaries and end conditions.
   - K5 State and data: what state exists, who owns it, where it lives and for how long, who may see it, and what
     happens on a concurrent change or a restart.
   - K6 Runtime and dependencies: language and runtime versions, allowed or forbidden dependencies, configuration
     (ports, environment variables, files).
   - K7 Structure: the modules or seams the behaviour needs so it can be tested and changed in isolation.
   - K8 Verification: the test framework, its command, and the check that observes each outcome at its real boundary.
   - K9 Delivery: where the result must run or be delivered, and the access that needs.
   - K10 Quality attributes: performance, security, accessibility, interface polish or other bounds.
   - K11 Risks: what would most likely make this work fail or be rejected, and what would show it early.
   - K12 Terms and references: the names, skills, commands, products and community phrases in the request, and the
     phrases that point at something it does not state ("the usual", "as before"); what each means here and where that
     was settled (the installed skills, the repository, or a search), else the best reading and how sure it is.
   - K13 Conflicts and premises: any two requirements, numbers or instructions in the request that contradict each
     other, and any claim about the existing system that the repository may contradict; the reading the run takes of
     each and who should confirm it.
   Terms and references: settle each by looking, in this order: the installed skills listed above, the repository and
   its documents, then a search (`research`). When nothing settles it, record the best reading and how sure you are as
   the `default`; use `person` only when two readings remain that lead to different work.

RULES:
- Attended: route an item to `person` only when the repository and the skills cannot settle it and two readings
  lead to different work; take the best default for everything else and record it as an assumption.

Result template:
```shiploop-state
{
  "evidence_refs": [],
  "headline": "<one line for the user: what this step established>",
  "outcome": "done",
  "question_categories": [{"applies": "yes", "id": "K1"}, {"applies": "no", "id": "K10", "reason": "..."}],
  "questions": [
    {"blocks": "...", "category": "...", "changes": "...", "default": "...", "id": "Q1", "question": "...", "route": "inspect|research|experiment|default|person"}
  ],
  "summary": "<one clause per request sentence S<n>: the outcome, boundary, default or open question it maps to>"
}
```
Fill the template: each key once, every placeholder (<...> and "...") replaced. Answer with the filled result only, in
one ```shiploop-state fenced block.

Original request (preserve user scope):
----- BEGIN ORIGINAL REQUEST -----
OK so this is for the tickets service in this folder, the help desk one.

What I want is that when an agent closes a ticket the requester gets the same kind of heads-up they get when it's resolved, but I don't want to send a second one if they just got one, so make it smart about that. It should go out right away, but also not spam people if an agent closes a pile of tickets in one go, so batch it, whatever's reasonable.

While you're in there, the list endpoint should let me see just the closed tickets from the usual window, there's a window we use for the weekly report I think, so use that. And the filters should work together, the way the docs say. I'm pretty sure they do already but double check.

I want you to run this as an until loop with the exit being green tests plus the thing actually working against a running server, and back-chain it first so we don't find preconditions halfway through. If you want to go ralph-style overnight that's fine, but put a cap on it so it doesn't run away. Tests should be real, not vibes, and no slop in the docs.

Don't touch the outbox retry logic, we're moving off OldTracker soon and I don't want to redo that twice. Keep it zero-dependency like the rest. The close should stay idempotent but also give a 409 if the ticket is already closed, whatever makes sense, and the audit log should say who closed it. Performance should be snappy, I don't care about exact numbers, but closing 500 tickets in one bulk call has to work.
----- END ORIGINAL REQUEST -----
Sentence index of this request (cite S<n>): S1: OK so this is for the tickets service in this folder, the help desk one. S2: What I want is that when an agent closes a ticket the requester gets the same kind of heads-up they get when it's resolved, but I don't want to send a second one if they just got one, so make it smart about that. S3: It should go out right away, but also not spam people if an agent closes a pile of tickets in one go, so batch it, whatever's reasonable. S4: While you're in there, the list endpoint should let me see just the closed tickets from the usual window, there's a window we use for the weekly report I think, so use that. S5: And the filters should work together, the way the docs say. S6: I'm pretty sure they do already but double check. S7: I want you to run this as an until loop with the exit being green tests plus the thing actually working against a running server, and back-chain it first so we don't find preconditions halfway through. S8: If you want to go ralph-style overnight that's fine, but put a cap on it so it doesn't run away. S9: Tests should be real, not vibes, and no slop in the docs. S10: Don't touch the outbox retry logic, we're moving off OldTracker soon and I don't want to redo that twice. S11: Keep it zero-dependency like the rest. S12: The close should stay idempotent but also give a 409 if the ticket is already closed, whatever makes sense, and the audit log should say who closed it. S13: Performance should be snappy, I don't care about exact numbers, but closing 500 tickets in one bulk call has to work.
