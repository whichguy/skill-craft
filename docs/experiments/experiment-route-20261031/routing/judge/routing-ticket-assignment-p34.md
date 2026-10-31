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
- Q1 [K1] How does the existing service identify agents and deliver assignment notifications, and what observable evidence confirms delivery? (changes: Notification implementation and its boundary test.)
- Q2 [K1] If no suitable notification mechanism exists, who decides the delivery channel and how an agent is reached? (changes: Notification requirement, integration, access and delivery test.)
- Q3 [K2] Which existing ticket operations and behaviours must assignment integrate with and preserve? (changes: Implementation scope and regression checks.)
- Q4 [K3] What are the existing API and CLI contracts, including response shapes, status codes, errors, ticket creation and listing formats? (changes: Assignment endpoint, ticket representations, CLI output and contract tests.)
- Q5 [K4] How does the service represent open and in-progress states, validate names and handle malformed bodies, missing tickets, repeated filters and no-op updates? (changes: Validation, edge-case responses and tests.)
- Q6 [K5] Where do tickets and shared state live, how long do they survive, who can see them, and what happens during concurrent updates or a restart? (changes: Assignment storage, visibility, consistency and persistence tests.)
- Q7 [K5] Where code, documentation or tests leave restart or concurrent-update behaviour uncertain, what does the running service actually do? (changes: Preservation requirements and restart or concurrency tests.)
- Q8 [K6] Which Node.js version, configuration and dependency constraints does the service currently require? (changes: Compatible implementation and execution environment.)
- Q9 [K7] Which existing modules and seams support isolated changes to ticket updates, filtering, notifications and CLI presentation? (changes: Code structure and isolation strategy.)
- Q10 [K8] How are existing tests organized and run, and how can the API, CLI and notification boundaries be observed? (changes: Test placement, fixtures and checks for each requested outcome.)
- Q11 [K9] What access and delivery steps are available for returning the changed service, and is any deployed target specified? (changes: Delivery and release steps.)
- Q12 [K10] What existing security and visibility controls apply to ticket details, agent identities and notifications? (changes: Access handling and security verification.)
- Q13 [K11] Do existing tests or service limitations expose compatibility risks, especially around ticket representations and notification delivery? (changes: Risk mitigation, test priorities and delivery readiness.)
- Q14 [K4] Does the existing notification convention resolve whether reassignment, unassignment, or an assignment that changes nothing produces a notification? (changes: Notification triggers and edge-case tests.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] After inspecting the existing API and CLI entry points, how do their current consumers observe ticket changes and listing output? (changes: Integration points and boundary-level acceptance checks.)
- Q2 [K2] What existing ticket operations and behaviours must assignment preserve, and how are ticket statuses represented? (changes: Compatibility requirements and the status check.)
- Q3 [K3] What response shapes, status codes, validation errors, ticket-not-found errors, and CLI output conventions does the service already use? (changes: The new endpoint contract, error handling, and CLI presentation.)
- Q4 [K4] After inspecting existing validation and status rules, how should whitespace-only or overlength names, missing or extra fields, repeated unassignment, and assignment attempts on other statuses behave? (changes: Validation, no-op handling, error responses, and edge-case tests.)
- Q5 [K5] How are tickets stored, initialized, shared, and updated across requests and restarts, and how are concurrent updates handled? (changes: Assignee initialization, persistence, update safety, and tests.)
- Q6 [K1] After discovery checks for an existing notification mechanism, agent identity, and delivery configuration, how can the assigned agent actually receive the notification? (changes: Notification transport, recipient resolution, observable success, and delivery requirements.)
- Q7 [K5] What actor identification, visibility controls, shared state, and session or notification lifetime does the runtime already provide? (changes: Recipient identification, privacy expectations, and notification handling.)
- Q8 [K4] After inspecting any existing notification semantics, when is a notification emitted, and what happens if delivery fails or an assignment is repeated? (changes: Notification triggers, failure handling, and tests.)
- Q9 [K6] What Node.js version, configuration, scripts, and dependency constraints does the repository require? (changes: Implementation syntax, runtime configuration, and commands.)
- Q10 [K7] Which existing modules and seams handle routing, tickets, filtering, CLI output, and any notifications? (changes: Placement and isolation of the new behaviour.)
- Q11 [K8] How do the existing node:test tests start the service and exercise the API and CLI, and what command runs the full suite? (changes: Test setup and checks for assignment, filtering, notification, CLI output, and compatibility.)
- Q12 [K9] Does the repository identify any delivery target or release process beyond returning changes to this service's source checkout? (changes: Delivery steps and required access.)
- Q13 [K10] What existing security, access-control, and operational bounds apply to ticket updates and notification delivery? (changes: Authorization, data exposure, and operational checks.)
- Q14 [K11] Do the current test suite and notification facilities expose compatibility or delivery risks before implementation? (changes: Verification order and the ability to complete notification delivery.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] After discovery identifies the API and CLI consumers and entry points, how can a real agent receive and observe an assignment notification, and how does the runtime identify that recipient? (changes: Notification delivery, recipient identification, and the boundary test.)
- Q2 [K2] After discovery reads the README, implementation, and existing tests, which existing ticket operations and CLI behaviors must remain compatible? (changes: Implementation scope and regression tests.)
- Q3 [K3] After discovery identifies the existing API conventions, what response shapes, status codes, and errors apply to assignment, unknown tickets, malformed bodies, invalid names, and disallowed ticket states? (changes: Endpoint contract and API tests.)
- Q4 [K4] After discovery establishes existing validation and ticket-state conventions, how are name length, whitespace-only names, name equality, repeated filters, and assignment to closed or otherwise ineligible tickets handled? (changes: Validation, matching rules, no-op behavior, and edge-case tests.)
- Q5 [K5] After discovery identifies storage, concurrency, restart behavior, authentication, and any notification state, where does the assignee live, who may see it, and how are concurrent updates and restarts handled? (changes: Data model, visibility, persistence, concurrency handling, and tests.)
- Q6 [K4] After discovery examines any notification mechanism and existing event semantics, when is a notification sent, and what happens if delivery fails or the assignee is unchanged or cleared? (changes: Notification trigger, failure behavior, and tests.)
- Q7 [K6] After discovery reads package metadata and runtime configuration, which Node.js versions, environment variables, and startup assumptions must the change support? (changes: Implementation compatibility and execution checks.)
- Q8 [K7] After discovery traces the server, ticket storage, CLI, and any notification seam, where can assignment and notification be isolated and tested while preserving existing structure? (changes: Module boundaries and testability.)
- Q9 [K8] After discovery reads the current tests and npm scripts, how can the API, CLI listing, state transitions, filters, and actual notification boundary be exercised with node:test? (changes: Test cases, fixtures, and verification commands.)
- Q10 [K9] After discovery inspects the checkout and execution environment, what repository changes and local access are needed for the API and CLI to be usable, and is any deployment target specified? (changes: Delivery steps and access requirements.)
- Q11 [K10] After discovery inspects existing security and operational conventions, are there established authorization, privacy, or performance bounds that assignment and notification must preserve? (changes: Access checks, data exposure, operational behavior, and relevant tests.)
- Q12 [K11] After discovery traces notification and existing ticket workflows, can the requested notification be delivered with the available runtime and without adding npm dependencies? (changes: Delivery feasibility, notification design, and early verification.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] After identifying the API and CLI consumers and entry points, how does the runtime identify agents and deliver notifications to them? (changes: Notification integration and its observable acceptance check.)
- Q2 [K1] If discovery finds no suitable notification mechanism or agent contact mapping, who can choose an authorized delivery channel and supply the required access? (changes: Notification destination, integration and delivery.)
- Q3 [K2] After reading the README, service, CLI and existing tests, which behaviours and dependency constraints must the change preserve? (changes: Implementation scope and regression checks.)
- Q4 [K3] After inspecting existing routes and tests, what response shapes, status codes, error formats, ticket representations and CLI listing format should the new behaviour follow? (changes: Endpoint and CLI contracts and boundary tests.)
- Q5 [K4] After inspecting validation and status conventions, how are missing or extra body fields, malformed JSON, unknown tickets, invalid names, terminal statuses, repeated filters and name equality handled? (changes: Validation, errors, assignment rules and edge-case tests.)
- Q6 [K5] After identifying ticket storage and lifecycle, how is state shared across requests, people, devices and sessions; what is its lifetime; what ends it; who can see it; and what happens on restart or concurrent changes? (changes: Assignee storage, privacy, concurrency and persistence tests.)
- Q7 [K5] After inspecting storage code and tests, what does the running service actually retain across restart and concurrent updates if that behaviour is not established by the evidence? (changes: Persistence and concurrency expectations and tests.)
- Q8 [K6] After reading package metadata and documentation, which Node.js version, configuration and runtime facilities does the service require? (changes: Compatible implementation and test execution.)
- Q9 [K7] After inspecting the server and CLI structure, which existing seams support isolated changes and tests, including notification delivery? (changes: Module boundaries and testability.)
- Q10 [K8] After inspecting the existing tests and npm scripts, how can each assignment, notification, filter and CLI outcome be observed at its real boundary while retaining the existing suite unchanged? (changes: New node:test cases and verification commands.)
- Q11 [K9] After inspecting the workspace and project documentation, is there an existing release target or access requirement beyond returning the modified service checkout? (changes: Delivery steps and access needs.)
- Q12 [K10] After inspecting existing validation, access controls and operational expectations, are there established security, performance or CLI presentation bounds that assignment and notification must preserve? (changes: Implementation constraints and quality checks.)
- Q13 [K11] After inspecting the notification and ticket-state paths, which integration or regression risks can be checked early at their actual boundaries? (changes: Test ordering and risk mitigation.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.