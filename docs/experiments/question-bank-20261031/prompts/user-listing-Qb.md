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
9. Key questions. Answer each key question below for this request before anything is planned. In `answers`,
   write one row per question: `id`, `basis` and `answer`. `basis` is the request sentence that settles the
   question (S1, S2, ...) or one of: inspect (the repository or environment answers it), research (documentation
   or other sources answer it), experiment (only running something answers it), default (no evidence can answer
   it, so the run assumes `answer` and records it), person (only a person can decide it; `answer` is then the
   default the run assumes), na (its answer would change nothing built, checked or delivered for this request;
   `answer` is a few words of reason). Otherwise `answer` is what the request settles or the answer the run
   assumes and records.
   - K1.1 Who uses the result, and through which entry point?
   - K1.2 What observation shows it works?
   - K2.1 What is in scope, and what is out?
   - K2.2 What existing behaviour must not change?
   - K3.1 What are the exact inputs, outputs, commands, endpoints, files or messages, and their names and shapes?
   - K3.2 What status codes and errors does each give?
   - K4.1 What are the domain rules, limits, boundaries and end conditions?
   - K4.2 Which inputs are invalid?
   - K5.1 What state exists, who owns it, and where does it live and for how long?
   - K5.2 Who may see it, and what happens on a concurrent change or a restart?
   - K6.1 Which language and runtime versions apply?
   - K6.2 Which dependencies are allowed or forbidden?
   - K6.3 What configuration does it need (ports, environment variables, files)?
   - K7.1 Which modules or seams does the behaviour need so it can be tested and changed in isolation?
   - K8.1 Which test framework and command run the tests?
   - K8.2 What check observes each outcome at its real boundary?
   - K9.1 Where must the result run or be delivered, and what access does that need?
   - K10.1 What performance, security, accessibility, interface polish or other bounds apply?
   - K11.1 What would most likely make this work fail or be rejected?
   - K11.2 What would show that early?

RULES:
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.

Result template:
```shiploop-state
{
  "evidence_refs": [],
  "headline": "<one line for the user: what this step established>",
  "outcome": "done",
  "answers": [
    {"answer": "...", "basis": "S1|inspect|research|experiment|default|person|na", "id": "K1.1"}
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
