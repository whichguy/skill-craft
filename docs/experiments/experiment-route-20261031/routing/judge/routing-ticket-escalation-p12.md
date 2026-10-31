You classify the questions that the first planning stage of a software-delivery run asked about a request to change an
existing system. For each question decide one class, by this rule only:

RUNTIME: settling it reliably needs the existing system observed while it runs: how fast or how much it handles, what it
keeps across a restart, a crash or a concurrent change, the exact output, order or shape it produces, or which of
conflicting sources (its code, its documents, its tests) holds.
NOT_RUNTIME: anything else: intent or policy the request leaves open, structure or conventions read from the code, the
delivery, or a decision only a person can make.

Judge each question on its own text. You are not told how anyone proposed to answer it, and the outputs are unlabeled.

Context: The repository exists: an existing Node.js service that an earlier run extended with ticket assignment; the next stage (discovery) will inspect it.

The request:
----- BEGIN REQUEST -----
Extend the ticket service with bulk reassignment and escalation. `POST /tickets/reassign` with `{"from": "<agent>", "to": "<agent>"}` moves every open or in-progress ticket assigned to `from` over to `to` and answers `{"moved": <how many>, "ids": [<their ids in id order>]}`; `from` and `to` must be two different agents. Each moved ticket's new agent is notified as for a single assignment. Urgent tickets must not wait unassigned: when an open, unassigned, urgent ticket is older than ESCALATE_AFTER_MINUTES minutes (an environment variable, default 60), the agent named in the ONCALL environment variable is notified that the ticket was escalated; without ONCALL nothing is escalated. A ticket is escalated at most once, even across restarts of the service. Everything the service already does keeps working, assignment included, and the existing tests must still pass. Add node:test tests for the new behaviour.
----- END REQUEST -----

===== OUTPUT O1 =====
- Q1 [K1] Who or what calls the ticket service, how are callers identified, and how are assignment and escalation notifications delivered and observed? (changes: The entry-point and notification checks, actor assumptions, and visibility boundaries.)
- Q2 [K2] What behavior and assignment changes did the earlier run deliver, and is any prior-run or recovery work incomplete? (changes: The preserved-behavior baseline and any recovery needed before extension.)
- Q3 [K3] What are the existing routing, agent and ticket representations, ID ordering, validation, and error conventions for the reassignment endpoint? (changes: Request validation, response ordering, status codes, error shapes, and contract tests.)
- Q4 [K4] How are ticket status, urgency, assignment, and age represented, and how are invalid escalation settings handled? (changes: Eligibility rules, time-boundary handling, configuration validation, and edge-case tests.)
- Q5 [K5] Where is ticket and notification state stored, what survives restart, and what happens when reassignment or escalation races with another change or a failure? (changes: Persistence, concurrency handling, escalation deduplication, and restart and race tests.)
- Q6 [K6] Which Node.js version, dependencies, startup configuration, and background-work mechanisms does the service already use? (changes: Implementation compatibility, environment-variable handling, and escalation scheduling.)
- Q7 [K7] Which existing modules isolate routing, ticket persistence, assignment notifications, and background work? (changes: The seams used to extend and independently test the behavior.)
- Q8 [K8] How are existing tests run, and which real service and notification boundaries can node:test observe? (changes: The test command and checks for reassignment, notifications, escalation, restart persistence, and preserved behavior.)
- Q9 [K9] What checkout and delivery process does this run use, and is a deployed target or release access specified by the environment? (changes: The delivery steps and when the result can be observed.)
- Q10 [K10] What existing authorization, privacy, and operational bounds apply to ticket changes and notifications? (changes: Access checks, data visibility, scheduling choices, and security or operational tests.)
- Q11 [K11] Can the existing persistence and notification mechanisms support the requested restart-safe, at-most-once escalation, and what failure modes do they expose? (changes: The escalation design, failure handling, and earliest feasibility checks.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] How do callers reach the ticket API, how are agents identified, and how do assignment notifications reach them? (changes: The entry-point and notification checks for both outcomes.)
- Q2 [K2] What behavior and artifacts from the earlier assignment run exist in this checkout, and what existing behavior must the change preserve? (changes: The implementation scope and regression checks.)
- Q3 [K3] What are the existing status codes, validation errors, ticket ID types and ordering convention, and notification message contracts? (changes: The endpoint contract and tests for valid and invalid requests.)
- Q4 [K4] How are open, in-progress, urgent, unassigned, ticket age, and agent validity represented, and how does the service handle notification failures? (changes: Eligibility, validation, error handling, and edge-case tests.)
- Q5 [K5] Where is ticket state persisted and shared, what survives restart, and what concurrency guarantees and visibility controls already exist? (changes: Durable escalation deduplication, reassignment consistency, and restart and concurrency tests.)
- Q6 [K6] Which Node.js version, dependencies, configuration conventions, and scheduling facilities does the service provide? (changes: Runtime compatibility, configuration parsing, and escalation scheduling.)
- Q7 [K7] Which existing modules or seams support assignment, persistence, notification, and time-dependent work? (changes: Where the behavior is implemented and how it can be tested independently.)
- Q8 [K8] How are the existing tests run, and what test facilities can observe the HTTP endpoint, notifications, elapsed time, and restart persistence? (changes: The node:test cases and regression verification commands.)
- Q9 [K9] What checkout and delivery mechanism does this run provide, and is there an explicitly named deployed target or required access? (changes: The delivery step and when users can observe the outcome.)
- Q10 [K10] What existing security, operational, and performance constraints apply to the endpoint and background escalation? (changes: Access controls, operational design, and relevant quality checks.)
- Q11 [K11] Can the existing persistence and notification mechanisms support at-most-once escalation through crashes and concurrent workers, and how can that be checked early? (changes: The escalation reliability design and failure or concurrency tests.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do callers reach the ticket API, how are agents identified, and how are assignment notifications observed? (changes: The entry-point and notification checks.)
- Q2 [K2] What behavior and assignment work from the earlier run must be preserved, and is there prior-run state or recovery guidance to reconcile? (changes: The preservation and recovery plan.)
- Q3 [K3] What are the existing API validation, status-code, error, ticket-ID ordering, and notification contracts for reassignment? (changes: The endpoint contract and its tests.)
- Q4 [K4] How are ticket status, urgency, age, agent validity, and assignment represented, and how should invalid escalation settings be handled under existing conventions? (changes: Eligibility rules, configuration validation, and edge-case tests.)
- Q5 [K5] What persistent state and concurrency controls exist, and how can escalation delivery be recorded across restarts without duplicate notifications or losing a pending escalation? (changes: The escalation state model, failure handling, and restart and concurrency tests.)
- Q6 [K6] Which Node.js version, dependencies, configuration mechanisms, and background execution facilities does the service provide? (changes: Runtime compatibility and escalation scheduling.)
- Q7 [K7] Which existing modules or seams own ticket updates, notifications, persistence, and time-dependent work? (changes: Where behavior is added and how it is isolated for testing.)
- Q8 [K8] What commands run the existing suite, and what fixtures or interfaces can verify the endpoint, notifications, timing, and restart behavior? (changes: The verification commands and boundary-level tests.)
- Q9 [K9] What repository delivery and prior-run recovery mechanisms are available, and does the request identify any deployed target? (changes: The delivery step and any required access.)
- Q10 [K10] What existing authorization, privacy, and operational constraints apply to ticket changes and agent notifications? (changes: Access controls and security and operational checks.)
- Q11 [K11] Can the existing persistence and notification mechanisms support at-most-once escalation across restarts and concurrent workers, including failures during notification? (changes: The escalation design, early feasibility check, and failure tests.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] Who can call the ticket API, how are callers identified, and through which existing mechanism do agents receive assignment and escalation notifications? (changes: Access handling and the observable API and notification checks.)
- Q2 [K2] What behavior, tests, and recoverable artifacts did the earlier assignment run leave in the current checkout, and is any prior-run work incomplete? (changes: The integration approach and regression coverage.)
- Q3 [K3] What are the existing ticket field names, agent identifiers, ID ordering convention, HTTP error conventions, and notification message contract? (changes: Request validation, response ordering, error behavior, and notification tests.)
- Q4 [K4] How are ticket status, urgency, creation age, and assignment represented, and how are invalid escalation configuration values handled elsewhere? (changes: Eligibility rules, threshold handling, configuration validation, and edge-case tests.)
- Q5 [K5] Where is ticket and notification state persisted, who can see it, and what actually happens to escalation and reassignment during restarts or concurrent changes? (changes: Durable escalation tracking, concurrency handling, visibility, and restart tests.)
- Q6 [K6] Which Node.js version, dependencies, environment configuration, and service startup commands does the repository support? (changes: Implementation compatibility, configuration, and test execution.)
- Q7 [K7] Which existing route, storage, scheduling, and notification seams can isolate the new behavior for testing? (changes: Module placement and test isolation.)
- Q8 [K8] What commands run the existing suite, and how can node:test observe the HTTP response, per-ticket notifications, escalation eligibility, and restart persistence at their real boundaries? (changes: Verification commands, fixtures, and acceptance checks.)
- Q9 [K9] What delivery or release mechanism and access, if any, are provided for the existing service? (changes: The delivery step and when users can observe the result.)
- Q10 [K10] What existing security, operational, and performance constraints govern bulk updates and background escalation? (changes: Authorization, scheduling, batch handling, and relevant checks.)
- Q11 [K11] Can the existing notification and persistence mechanisms meet at-most-once escalation across crashes, and what failure behavior do they expose? (changes: Failure handling, the escalation guarantee, and early risk tests.)
- Q12 [K4] Does escalation assign the ticket to the on-call agent or change its status? (changes: Ticket mutation requirements and escalation tests.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.