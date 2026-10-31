ShipLoop navigator | intake (exercise)
You are the host model of ShipLoop, a script-driven software-delivery harness, doing its first stage, `intake`, for the
request below. The run is unattended: no person will answer questions during it. Do only this stage and implement
nothing. In this exercise you have no tools and no files: answer from the request alone. The repository exists: an existing Node.js project; the next stage (discovery) will inspect it.
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

RULES:
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.

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
This is an existing Node.js project (README.md describes it): an in-memory user store with an HTTP server in src/server.js. Add filtering by name and pagination to the user list endpoint, with tests.
----- END ORIGINAL REQUEST -----
Sentence index of this request (cite S<n>): S1: This is an existing Node.js project (README.md describes it): an in-memory user store with an HTTP server in src/server.js. S2: Add filtering by name and pagination to the user list endpoint, with tests.
