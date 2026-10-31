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
- Q1 [K1] Which existing clients, actors and notification entry points use ticket assignment, and how does the runtime identify agents? (changes: Consumer-facing behavior and boundary checks.)
- Q2 [K2] What behavior and prior-run assignment changes already exist and must remain compatible? (changes: Implementation scope and regression tests.)
- Q3 [K3] What validation, response status, error shapes, agent identifiers and ID ordering does the existing service use, and could the new route conflict with another route? (changes: The endpoint contract and API tests.)
- Q4 [K4] How are open, in-progress, urgent, unassigned and ticket age represented, and how does single-assignment notification behave on failure? (changes: Eligibility, reassignment notification semantics and edge-case tests.)
- Q5 [K5] Where is ticket state persisted, how are concurrent updates handled, and what durable mechanism can prevent repeat escalation across restarts? (changes: Escalation state ownership, persistence and concurrency tests.)
- Q6 [K5] What does the existing service expose or hide about tickets, agents and notifications across callers and sessions? (changes: Data visibility and authorization checks.)
- Q7 [K6] Which Node.js version, dependencies, configuration conventions and background execution facilities are available? (changes: Scheduler, configuration parsing and compatibility decisions.)
- Q8 [K4] How should invalid escalation thresholds, the exact age boundary and escalation timing be handled if existing conventions do not settle them? (changes: Configuration behavior and timing tests.)
- Q9 [K7] Which existing seams permit isolated reassignment, notification, clock and persistence testing? (changes: Module boundaries and test design.)
- Q10 [K8] What commands run the existing suite, and how can node:test observe the endpoint, notification, timing and restart boundaries? (changes: Verification commands and acceptance tests.)
- Q11 [K9] What checkout and delivery mechanism does this run provide, and is any deployed target or release access specified? (changes: Delivery steps and where the outcome can be observed.)
- Q12 [K10] What existing security and operational limits apply to the new endpoint and background escalation? (changes: Access controls and operational checks.)
- Q13 [K11] Can the existing storage and notification mechanism satisfy at-most-once escalation under crashes and concurrent workers, and what failure behavior follows? (changes: Delivery risk assessment, escalation design and failure tests.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] Who calls the ticket service and receives assignment notifications, and how are callers and agents identified? (changes: Entry-point checks, notification integration, and tests.)
- Q2 [K2] What behavior and assignment changes from the earlier run exist in the current checkout, and are there prior-run records or unfinished changes to preserve? (changes: Implementation scope, recovery approach, and regression checks.)
- Q3 [K3] What are the existing request validation, error responses, ticket ID ordering, and assignment notification contracts? (changes: Endpoint responses, validation, notification calls, and contract tests.)
- Q4 [K4] How are open, in-progress, urgent, unassigned, ticket age, and agent validity represented, and how are invalid escalation settings handled? (changes: Eligibility, validation, configuration handling, and edge-case tests.)
- Q5 [K5] Where does ticket and escalation state live, who can see it, and how are concurrent changes and restarts handled? (changes: Durable at-most-once escalation design, access boundaries, and concurrency and restart tests.)
- Q6 [K5] What actually persists across a restart, and what happens when reassignment or escalation races with another ticket change or worker? (changes: Concurrency safeguards and restart verification.)
- Q7 [K6] Which Node.js version, dependencies, environment configuration, and scheduling mechanisms does the service already use? (changes: Compatible implementation, configuration, and execution commands.)
- Q8 [K7] Which existing router, assignment, notification, storage, and scheduling seams can support the new behavior in isolation? (changes: Module boundaries and test setup.)
- Q9 [K8] What commands run the existing suite and node:test tests, and how can the endpoint, notifications, elapsed time, and restart behavior be observed at their real boundaries? (changes: Test commands, fixtures, and verification coverage.)
- Q10 [K9] What checkout, run commands, and access are available for delivering and verifying the service change? (changes: Delivery and verification steps.)
- Q11 [K10] What existing security and operational bounds apply to the endpoint and escalation checks? (changes: Authorization, operational design, and quality checks.)
- Q12 [K11] Can the existing notification and storage mechanisms support durable at-most-once escalation without losing required notifications, and what failure behavior do they provide? (changes: Failure handling, feasibility assessment, and early risk checks.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do callers reach the ticket API, how are actors identified, and how are assignment and escalation notifications observed? (changes: Consumer, entry-point, authorization and end-to-end test decisions.)
- Q2 [K2] What did the earlier assignment run deliver, what recovery or handoff artifacts exist, and which existing behaviors and tests must be preserved? (changes: Implementation scope, recovery decisions and regression tests.)
- Q3 [K3] What are the existing agent and ticket representations, ID ordering, validation conventions, response statuses and errors, and assignment notification payload? (changes: Request validation, response contract, notification integration and contract tests.)
- Q4 [K4] How does the service represent ticket status, urgency and age, and how should eligibility be evaluated at the threshold and when ticket state changes? (changes: Selection rules and boundary tests.)
- Q5 [K5] Where is ticket state stored, who can read or change it, what survives restarts, and what atomic operations or concurrency controls are available for reassignment and escalation? (changes: Persistence, visibility, concurrency and restart-test decisions.)
- Q6 [K5] What notification delivery guarantees and failure behavior does the existing mechanism provide, especially if the service stops between recording escalation and sending a notification? (changes: At-most-once implementation, failure handling and restart tests.)
- Q7 [K6] Which Node.js version, dependencies, configuration conventions and background scheduling facilities does the service use? (changes: Runtime compatibility, scheduling and configuration decisions.)
- Q8 [K4] How does existing configuration handle an invalid escalation threshold or an empty ONCALL value, and what scan cadence can the runtime support? (changes: Configuration validation, escalation timing and tests.)
- Q9 [K7] Which existing modules isolate ticket updates, assignment notifications, persistence and background work? (changes: Integration seams and independently testable design.)
- Q10 [K8] What commands run the existing suite, and how can node:test observe the real endpoint, notifier, clock and persistent restart behavior? (changes: Verification commands, fixtures and boundary tests.)
- Q11 [K9] What checkout, handoff or release process and access are available for this existing service? (changes: Delivery steps and where the result becomes usable.)
- Q12 [K10] What existing security, operational and performance constraints govern bulk updates and background notifications? (changes: Authorization, resource-use decisions and quality checks.)
- Q13 [K11] Can the existing persistence and notification boundaries support durable at-most-once escalation under concurrent workers, failures and restarts? (changes: Feasibility, risk handling and early verification.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] How do service consumers call ticket endpoints, and how are agents identified and notified for a single assignment? (changes: The integration and observable notification checks for reassignment and escalation.)
- Q2 [K2] What existing ticket and assignment behavior, prior-run changes, and recovery context must be preserved? (changes: The compatibility boundary and regression checks.)
- Q3 [K3] What are the existing ticket ID types, ordering convention, request validation, response status codes, and error formats? (changes: The reassignment endpoint contract and boundary tests.)
- Q4 [K4] How does the service represent agent validity, ticket status, urgency, assignment, and ticket age? (changes: Eligibility, validation, and edge-case tests for both features.)
- Q5 [K4] What should happen when agent inputs or ESCALATE_AFTER_MINUTES are invalid, or the threshold is exactly reached? (changes: Validation and boundary tests.)
- Q6 [K5] Where is ticket state stored, what persists across restarts, and how are concurrent updates coordinated? (changes: Durable escalation tracking, reassignment consistency, and restart and concurrency tests.)
- Q7 [K5] What actually happens to persisted tickets and escalation state across a restart and concurrent eligibility checks? (changes: The implementation and tests for at-most-once escalation.)
- Q8 [K5] Who may see ticket and notification data, and does the runtime identify callers or agents across sessions and devices? (changes: Authorization, visibility, and data-handling tests.)
- Q9 [K6] Which Node.js version, dependencies, environment configuration, and scheduling facilities does the service provide? (changes: The escalation execution mechanism and configuration handling.)
- Q10 [K7] Which existing modules or seams support isolated ticket updates, notifications, time, persistence, and scheduling? (changes: Module placement and testability.)
- Q11 [K8] What command runs the existing suite, and how can node:test exercise the HTTP boundary, notifications, time, and restart behavior? (changes: The verification commands and outcome checks.)
- Q12 [K9] What checkout and delivery process continue the earlier run, and is there an authorized deployed target? (changes: The delivery step and access requirements.)
- Q13 [K10] Are there established latency, security, or notification-delivery requirements that constrain bulk reassignment or escalation? (changes: Operational design and acceptance checks.)
- Q14 [K11] How does the existing notification mechanism behave on failure, and can its effects and the escalation record be coordinated across crashes? (changes: Failure handling and tests for the at-most-once escalation guarantee.)
- Q15 [K4] How promptly must an eligible ticket be checked and notified, and what happens if ONCALL changes? (changes: Scheduling and configuration-reload decisions and their tests.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.