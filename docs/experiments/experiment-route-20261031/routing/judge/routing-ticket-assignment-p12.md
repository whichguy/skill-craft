You classify the questions that the first planning stage of a software-delivery run asked about a request to change an
existing system. For each question decide one class, by this rule only:

RUNTIME: settling it reliably needs the existing system observed while it runs: how fast or how much it handles, what it
keeps across a restart, a crash or a concurrent change, the exact output, order or shape it produces, or which of
conflicting sources (its code, its documents, its tests) holds.
NOT_RUNTIME: anything else: intent or policy the request leaves open, structure or conventions read from the code, the
delivery, or a decision only a person can make.

Judge each question on its own text. You are not told how anyone proposed to answer it, and the outputs are unlabeled.

Context: The repository exists: an existing Node.js service; the next stage (discovery) will inspect it.

The request:
----- BEGIN REQUEST -----
This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSON body `{"assignee": "<agent>"}` assigns the ticket to that agent, and `{"assignee": null}` unassigns it; an agent is a non-empty name of at most 64 characters. Only open and in-progress tickets can be assigned or unassigned. Assigning a ticket to the agent it already has changes nothing. Every ticket shows its `assignee` (null when unassigned). The agent a ticket is assigned to is notified that it was assigned to them. `GET /tickets` gains an `assignee` filter: `assignee=<agent>` keeps that agent's tickets and an empty `assignee=` keeps the unassigned ones; a ticket must match every filter given. The command-line listing shows each ticket's assignee. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.
----- END REQUEST -----

===== OUTPUT O1 =====
- Q1 [K1] How does the service identify and notify an assigned agent, and how can receipt be observed? Discovery must first inspect existing agent identity, notification facilities, documentation and configuration. (changes: Notification mechanism, recipient identification and end-to-end verification.)
- Q2 [K2] What existing ticket operations and behaviours must assignment preserve? Discovery must first read the service, README and existing tests. (changes: Regression boundaries and implementation scope.)
- Q3 [K3] What response shapes, status codes, errors and CLI formatting conventions apply to ticket updates, invalid bodies, unknown tickets and listings? Discovery must first inspect existing routes, CLI and tests. (changes: Endpoint and CLI contracts and their tests.)
- Q4 [K4] How are statuses and names represented, and how should whitespace-only names, character counting, invalid assignee values, repeated filters and notifications on reassignment be handled? Discovery must first inspect validation, status transitions, filtering and notification conventions. (changes: Validation, eligibility, filtering and notification tests.)
- Q5 [K5] Where do tickets live, how are updates synchronized and persisted, what survives a restart, and what access controls or shared-session semantics already exist? Discovery must first inspect storage, runtime and tests. (changes: Assignment storage, concurrent-update handling, visibility and restart tests.)
- Q6 [K6] Which Node.js version, configuration and dependency constraints does the service actually use? Discovery must first inspect package metadata, runtime configuration and README. (changes: Compatible implementation and test commands.)
- Q7 [K7] Which existing modules or seams isolate routing, ticket state, CLI output and any notification mechanism? Discovery must first inspect the source layout and tests. (changes: Placement of changes and isolated verification.)
- Q8 [K8] How are existing node:test tests started, and how can tests observe the HTTP API, CLI, state changes and agent notification at their real boundaries? Discovery must first inspect test files, package scripts and notification facilities. (changes: Test setup, assertions and verification commands.)
- Q9 [K9] What checkout and execution environment are available, and does the request identify any deployed target? Discovery must first inspect the workspace and delivery configuration. (changes: Delivery location, required access and release steps.)
- Q10 [K10] What existing security, performance and CLI presentation constraints apply to these operations? Discovery must first inspect documented constraints and established behaviour. (changes: Implementation bounds and relevant checks.)
- Q11 [K11] Do the current architecture and available runtime support reliable notification and assignment updates without breaking existing behaviour? Discovery must first inspect integration points, storage and the existing test baseline. (changes: Feasibility, risk handling and early verification.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] How does the existing runtime identify agents and deliver notifications to them, and what observable event proves delivery? (changes: Notification design and its boundary test.)
- Q2 [K1] If discovery finds no usable notification mechanism, what channel and delivery contract should notify an agent identified only by name? (changes: Notification requirement, integration and delivery.)
- Q3 [K2] What existing ticket operations, CLI behavior and tests must assignment preserve? (changes: Compatibility requirements and regression checks.)
- Q4 [K3] What are the existing response shapes, status codes, error conventions and CLI listing format, and how should the new endpoint and field fit them? (changes: API and CLI contracts and their tests.)
- Q5 [K4] How does the service represent ticket statuses and validate names and JSON, including missing, non-string, empty and overlength assignees? (changes: Validation rules, eligibility checks and edge-case tests.)
- Q6 [K4] When assignment changes, which transitions trigger notification, including reassignment, unassignment and an unchanged assignee? (changes: Notification behavior and tests.)
- Q7 [K5] Where do tickets live, how are they shared and protected, and what happens to updates across concurrent requests and restarts? (changes: Assignee storage, visibility, concurrency and persistence tests.)
- Q8 [K6] Which Node.js version, configuration and dependency constraints does the repository establish? (changes: Implementation choices and executable test commands.)
- Q9 [K7] What existing modules and seams support isolated assignment, notification and CLI tests? (changes: Code placement and test design.)
- Q10 [K8] How do existing node:test tests start the service and exercise API and CLI boundaries? (changes: New test setup and verification.)
- Q11 [K9] What checkout and execution environment does discovery expose for implementing and verifying the service? (changes: Delivery and verification steps.)
- Q12 [K10] Are there existing security, performance or interface constraints relevant to assignment and notification? (changes: Implementation bounds and acceptance checks.)
- Q13 [K11] Do the existing code, documentation and tests agree about ticket state, filtering and notification capabilities? (changes: Risk assessment, implementation and regression tests.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How are agents identified and reached, and what existing notification capability can deliver an assignment notice to the assigned agent? (changes: Notification integration, recipient identification, and the observable delivery test.)
- Q2 [K2] Which existing ticket operations, status transitions, filters, CLI behavior, and compatibility guarantees must assignment preserve? (changes: Implementation scope and regression tests.)
- Q3 [K3] What existing API conventions determine the assignment endpoint's response shape, status codes, errors, missing-ticket handling, and malformed or missing assignee handling? (changes: Endpoint contract and boundary tests.)
- Q4 [K4] How are status names represented, and how does the service interpret name length, whitespace, case, repeated filters, and an assignment to the current agent? (changes: Validation, matching, idempotence, notification behavior, and edge-case tests.)
- Q5 [K5] Where and for how long are tickets stored, how is state shared across requests and clients, and what happens on concurrent updates or restart? (changes: Assignee storage, migration or initialization, concurrency behavior, and persistence tests.)
- Q6 [K5] Does the runtime identify users or agents and restrict ticket or notification visibility? (changes: Recipient mapping, data visibility, and authorization tests.)
- Q7 [K6] Which Node.js versions, configuration, startup conventions, and dependency constraints does the service actually support? (changes: Compatible implementation, notification configuration, and test execution.)
- Q8 [K7] Which existing modules and seams support ticket updates, filtering, CLI output, and observable notification delivery? (changes: Placement and isolation of the new behavior.)
- Q9 [K8] How are existing node:test tests started, and how can tests observe the API, CLI, state changes, and actual notification boundary? (changes: Test setup, npm test integration, and acceptance checks.)
- Q10 [K9] What repository checkout and execution environment will receive and run the changes, and is any separate release target specified? (changes: Delivery location and verification commands.)
- Q11 [K10] Do existing service contracts impose security, performance, or CLI presentation bounds relevant to assignment and notification? (changes: Validation, access controls, output formatting, and quality checks.)
- Q12 [K11] Can notification delivery fail, and does an existing contract specify whether assignment succeeds, fails, or retries when it does? (changes: Failure handling, consistency, and notification failure tests.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] How are agents identified and reached, and what observable notification mechanism already exists for an assignment? (changes: The notification requirement, recipient resolution, delivery design and boundary test.)
- Q2 [K2] What existing ticket operations and behaviours must assignment preserve, including creation and updates? (changes: The implementation scope and regression checks.)
- Q3 [K3] What response shapes, status codes and errors do existing endpoints use for successful updates, missing tickets, invalid bodies and disallowed state changes? (changes: The assignment endpoint contract and its tests.)
- Q4 [K4] How does the service represent ticket statuses and validate names, and how should whitespace, character length, extra fields and repeated assignment or unassignment be handled? (changes: Validation, eligibility, idempotence and edge-case tests.)
- Q5 [K5] Where are tickets stored, who can access them, how long do they persist, and what happens on restart or concurrent updates? (changes: Assignee persistence, visibility, concurrency handling and tests.)
- Q6 [K6] Which Node.js version, configuration and dependency constraints does the service actually use? (changes: Implementation compatibility and commands used for verification.)
- Q7 [K7] What existing modules or seams support ticket changes, filtering, CLI rendering and notification testing? (changes: Placement and isolation of the new behaviour.)
- Q8 [K8] How are existing node:test tests run, and how can the API, CLI and notification outcomes be observed at their actual boundaries? (changes: Test setup, fixtures and acceptance checks.)
- Q9 [K9] Does the repository identify a release target or delivery process beyond the requested service checkout? (changes: The delivery steps and any required access.)
- Q10 [K10] Are there established security, performance or CLI presentation constraints relevant to assignment and notifications? (changes: Access checks, notification handling and acceptance criteria.)
- Q11 [K11] Can an assignment and its notification be coordinated under the existing runtime, including notification failure and repeated requests? (changes: Failure semantics, duplicate-notification handling and early risk tests.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.