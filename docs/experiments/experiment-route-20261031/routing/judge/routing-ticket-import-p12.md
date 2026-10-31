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
This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add a bulk import for the help desk's move from its old tracker. `POST /tickets/import` takes a JSON body `{"tickets": [...]}` whose items are what `POST /tickets` takes, at most 5000 of them, and creates them in the given order: all of them, or none when any item is invalid, in which case it answers 400 with an error whose message names the first invalid item by its index in the array (0 for the first). On success it answers 201 with `{"created": <how many>, "ids": [<the new ids in order>]}`. Each imported ticket is recorded and its requester is notified just as when one ticket is created. An import of 5000 tickets must be answered within 10 seconds. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.
----- END REQUEST -----

===== OUTPUT O1 =====
- Q1 [K1] How do callers reach the existing API, and what observable storage and notification effects accompany a single-ticket creation? (changes: The import's integration point and boundary-level acceptance checks.)
- Q2 [K2] Which existing API, command-line and service behaviours must the import coexist with, including route matching? (changes: The integration approach and regression coverage.)
- Q3 [K3] What exact ticket fields, validation rules, error shape and ID format does single-ticket creation use? (changes: Import validation, indexed error responses and success-response tests.)
- Q4 [K4] How does the service handle malformed JSON and invalid request shapes, and what should happen for an empty array or more than 5000 items? (changes: Request-boundary validation and edge-case tests.)
- Q5 [K5] Where do tickets and notification records live, how are IDs assigned, and how do concurrent requests and restarts affect them? (changes: Ordered ID allocation, atomic validation, concurrency handling and persistence tests.)
- Q6 [K5] What happens if recording or notifying fails after validation, and what mechanism can preserve the existing single-ticket semantics without leaving an invalid batch partially created? (changes: Side-effect ordering, failure handling and tests.)
- Q7 [K6] Which Node.js version, configuration, body-size limits and dependency constraints govern the service? (changes: Implementation compatibility and whether a 5000-ticket request can reach the handler.)
- Q8 [K7] Which existing modules or seams support shared ticket validation, creation, recording and notification? (changes: The smallest testable integration that preserves single-ticket behaviour.)
- Q9 [K8] How do existing node:test tests start the service and observe tickets and notifications, and what command runs the complete suite? (changes: New boundary-level tests and regression verification.)
- Q10 [K9] What checkout and delivery mechanism does the harness provide for returning the changed service? (changes: The final delivery step and the point at which the result is visible.)
- Q11 [K10] What representative ticket data, notification behaviour and execution environment should measure the 5000-ticket, 10-second response bound? (changes: The performance test setup and evidence for the timing requirement.)
- Q12 [K11] Do request-size limits, per-ticket I/O, notification latency or state updates threaten atomicity or the timing bound? (changes: The implementation approach and early risk checks.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] How do callers reach the existing ticket API and observe a single creation and its requester notification? (changes: The boundary checks for the import consumer and notification behavior.)
- Q2 [K2] Which existing API, command-line, and other service behaviors and tests must be preserved? (changes: Regression coverage and implementation boundaries.)
- Q3 [K3] What exact ticket input, identifier, error envelope, and malformed-body behavior does the existing API use? (changes: Import validation, response formatting, and contract tests.)
- Q4 [K4] What are the existing ticket validation rules, and how should an empty array, a missing or non-array tickets field, and more than 5000 items be handled? (changes: Validation decisions and edge-case tests.)
- Q5 [K5] How are tickets and notifications stored, ordered, and made visible across requests, concurrent imports, and restarts, and what can be rolled back? (changes: Atomicity design, ordering guarantees, and state and concurrency tests.)
- Q6 [K6] Which Node.js version, configuration, scripts, and built-in facilities are available? (changes: Compatible implementation and test commands.)
- Q7 [K7] Which existing seams can share single-ticket validation, recording, and notification with bulk import? (changes: Module boundaries and isolated verification.)
- Q8 [K8] How do existing node:test tests start the service, control side effects, and observe API outcomes? (changes: New test setup and real-boundary checks.)
- Q9 [K9] What checkout and execution environment will receive and run the service changes, and is any release target specified? (changes: Delivery and verification steps.)
- Q10 [K10] Can the existing service process and answer a valid 5000-ticket import within 10 seconds under the available test environment? (changes: Performance design and acceptance verification.)
- Q11 [K11] Do recording or notification failures, request-size limits, or route matching prevent atomic invalid-item handling or the required bulk response? (changes: Failure handling, implementation design, and early risk checks.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do clients reach the ticket API and observe ticket creation and requester notification? (changes: Boundary tests and how the migration consumer observes success.)
- Q2 [K2] Which existing API and command-line behaviors must regression checks preserve? (changes: Implementation boundaries and regression coverage.)
- Q3 [K3] What exact ticket fields, response and error shapes, routing rules and body limits does the existing service use? (changes: Import validation, error responses and endpoint integration.)
- Q4 [K4] How should empty imports, missing or non-array tickets, malformed JSON and imports over 5000 items be handled under existing conventions? (changes: Validation rules, status codes and edge-case tests.)
- Q5 [K5] Where are tickets and notification effects stored, how are IDs allocated, and what happens on concurrent requests, restart or a creation or notification failure? (changes: Atomic validation, ordering, failure handling and state tests.)
- Q6 [K6] What Node.js versions, configuration, request-size limits and dependency constraints apply? (changes: Compatible implementation, configuration and verification.)
- Q7 [K7] What existing validation, creation and notification seams can be reused while validating the full batch before side effects? (changes: Module boundaries and isolation of the import behavior.)
- Q8 [K8] How do existing node:test tests start the service and observe persistence and notifications, and how can the import be checked at its HTTP boundary? (changes: Test setup and checks for success, ordering, indexed rejection, side effects and regressions.)
- Q9 [K9] What delivery mechanism and access does this run provide for returning the changed service? (changes: Final delivery step and where the outcome becomes usable.)
- Q10 [K10] What representative valid 5000-ticket workload and timing method can exercise the HTTP response within 10 seconds in the available environment? (changes: Performance implementation and verification.)
- Q11 [K11] Do request-size limits, synchronous notification or storage behavior prevent atomic invalid-item rejection or the 10-second target? (changes: Implementation approach and early risk checks.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] Which existing HTTP entry point and ticket-creation path serve API consumers, and how can discovery observe recording and notification? (changes: Integration and observable acceptance checks)
- Q2 [K2] Which existing API, command-line, and other behaviors and tests must be preserved? (changes: Regression scope and integration decisions)
- Q3 [K3] What are the existing ticket input schema, response and error conventions, and route-matching rules? (changes: Import validation, error shape, and endpoint integration)
- Q4 [K4] How does the service handle malformed JSON and invalid fields, and what should an empty import, a missing or non-array tickets field, or more than 5000 items do? (changes: Boundary rules and invalid-input tests)
- Q5 [K5] Where are tickets and IDs stored, how are they shared and retained, and what happens during concurrent requests or a restart? (changes: Atomic validation, ID ordering, state handling, and concurrency tests)
- Q6 [K5] What happens if recording or notifying fails after validation, and can existing side effects be rolled back? (changes: Failure handling and tests for import side effects)
- Q7 [K6] Which Node.js versions, configuration, dependency constraints, and request-body limits does the service use? (changes: Compatibility, configuration, and handling of a 5000-item request)
- Q8 [K7] Which existing modules or seams support shared validation and creation without changing single-ticket behavior? (changes: Code structure and isolation of tests)
- Q9 [K8] How does the existing node:test suite start the service and observe responses, storage, and notifications? (changes: New test setup and checks at the HTTP boundary)
- Q10 [K9] What checkout and runtime does the harness provide for delivery and verification, and is a deployed target specified? (changes: Delivery and validation steps)
- Q11 [K10] Can the existing service record and notify 5000 valid tickets and answer within 10 seconds in the available runtime? (changes: Performance design and verification)
- Q12 [K11] Do body-size limits, validation side effects, notification costs, or storage behavior threaten atomic rejection or the time limit? (changes: Early feasibility checks and implementation priorities)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.