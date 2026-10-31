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
- Q1 [K1] How do callers reach the existing API, and what observable recording and notification effects demonstrate a successful single-ticket creation? (changes: The import integration and its boundary checks.)
- Q2 [K2] Which existing API and command-line behaviours and tests must the change preserve? (changes: The implementation boundary and regression checks.)
- Q3 [K3] What are the existing ticket input schema, error envelope, body parsing and routing conventions, including handling of malformed JSON and an absent or non-array tickets field? (changes: Import validation, response shapes and API tests.)
- Q4 [K4] How should an array over 5000 items and an empty array be handled, and which validation rules determine the first invalid item? (changes: Limit and validation behaviour and edge-case tests.)
- Q5 [K5] Where are tickets and notification effects stored, how are IDs allocated, and what happens on concurrent requests, restarts or failures during recording or notification? (changes: Atomicity, ordering, failure handling and state tests.)
- Q6 [K6] Which Node.js versions, configuration, dependency constraints and runtime facilities does the service support? (changes: Implementation choices and execution environment.)
- Q7 [K7] Which existing validation, creation, recording and notification seams can be reused or isolated for a batch? (changes: Module structure and testability.)
- Q8 [K8] How do existing node:test tests start the service and observe HTTP responses, stored tickets and notifications? (changes: New test setup and checks at the real API boundary.)
- Q9 [K9] Does the repository identify a release target or delivery mechanism beyond returning the changed source checkout? (changes: Delivery steps and access requirements.)
- Q10 [K10] What representative runtime and notification setup can exercise a 5000-ticket request and measure its response time at the HTTP boundary? (changes: The performance test setup and evidence for the 10-second requirement.)
- Q11 [K11] Can the existing recording and notification mechanisms support ordered imports, validation atomicity and the time bound together? (changes: The implementation approach, early feasibility checks and any unresolved delivery risk.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] Who calls the existing ticket API, how are callers identified, and what runtime behavior is already provided? (changes: Consumer assumptions, authorization behavior and boundary tests.)
- Q2 [K2] What existing API and command-line behavior must be preserved, including any route-order interactions with the new endpoint? (changes: Implementation scope and regression checks.)
- Q3 [K3] What exact ticket input, validation, error envelope, ID format and HTTP parsing behavior does single-ticket creation use? (changes: Import request handling, error response and contract tests.)
- Q4 [K4] How should malformed bodies, a missing or non-array tickets field, an empty array and more than 5000 items be handled? (changes: Boundary rules, status codes and tests.)
- Q5 [K5] Where are tickets and notifications stored or sent, what is shared across callers or restarts, who can see it, and how are concurrent writes handled? (changes: Atomicity strategy, state visibility and concurrency tests.)
- Q6 [K5] What happens if recording or notification fails after validation, and what guarantees does single-ticket creation already provide? (changes: Failure handling and tests for partial side effects.)
- Q7 [K6] Which Node.js versions, request-size limits, configuration and dependency constraints does the service actually use? (changes: Compatible implementation and the ability to accept a 5000-ticket request.)
- Q8 [K7] Which existing validation, ticket creation, recording and notification seams can support ordered bulk processing without changing single-ticket behavior? (changes: Module boundaries and isolation strategy.)
- Q9 [K8] How do existing node:test suites start the service and observe storage and notifications, and how can the import be checked at its HTTP boundary? (changes: Test setup and verification of ordering, atomic invalid-item rejection, side effects and compatibility.)
- Q10 [K9] What checkout and execution environment will receive the change, and is any release target or release access specified elsewhere in the repository? (changes: Delivery steps and where the result can be observed.)
- Q11 [K10] What representative 5000-ticket payload and environment can exercise the ten-second limit, including normal recording and notification work? (changes: Performance test and implementation decisions.)
- Q12 [K11] Do existing synchronous side effects, request limits or storage behavior threaten the deadline or invalid-item atomicity? (changes: Risk mitigation and early verification.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do existing API consumers reach and identify themselves to the service, and how can an import and its notifications be observed? Discovery should first inspect the README, server, and existing tests. (changes: The entry point and observable acceptance checks.)
- Q2 [K2] Which existing API and command-line behaviors must regression checks cover? Discovery should first inspect the README, bin/, and existing tests. (changes: Regression coverage and preservation decisions.)
- Q3 [K3] What exact ticket input, validation order, error shape, and creation response does POST /tickets use? Discovery should first inspect its handler and tests. (changes: Import validation, error formatting, and compatibility tests.)
- Q4 [K4] How should empty arrays, missing or non-array tickets, malformed JSON, and arrays over 5000 be handled? Discovery should first inspect existing request and error conventions. (changes: Boundary rules and invalid-request tests.)
- Q5 [K5] Where do tickets and notifications live, who can see them, and what are their lifetimes? Discovery should first trace single-ticket creation, storage, and notification code. (changes: Import persistence, visibility, notification behavior, and tests.)
- Q6 [K5] What happens to ticket state and notifications during concurrent changes, failures, and restarts? Discovery should first inspect storage and notification mechanisms, then run targeted experiments where their behavior is not established. (changes: Atomicity design and failure, concurrency, and restart tests.)
- Q7 [K6] Which Node.js versions, configuration, request-size limits, and dependency constraints apply? Discovery should first inspect package metadata, README, and server configuration. (changes: Runtime compatibility, request handling, and verification setup.)
- Q8 [K7] Which existing modules or seams support shared validation, recording, and notification without changing single-ticket behavior? Discovery should first trace the existing creation path. (changes: Implementation structure and isolation of tests.)
- Q9 [K8] How do the existing node:test suite and npm test command exercise the real HTTP and side-effect boundaries? Discovery should first inspect package scripts and test/. (changes: Test setup and checks for ordering, atomicity, recording, notification, and regression.)
- Q10 [K9] Does the repository specify a delivery or deployment target beyond this source checkout? Discovery should first inspect the README and repository configuration. (changes: Delivery steps and any required access.)
- Q11 [K10] Can the existing service record and notify for 5000 valid tickets within 10 seconds, and what request-size or resource limits affect the measurement? Discovery should first identify the runtime, representative valid input, and side-effect mechanisms, then measure the running service. (changes: Performance design and the 5000-ticket acceptance test.)
- Q12 [K11] Do request parsing, storage, or notification constraints threaten atomicity, existing behavior, or the 10-second limit? Discovery should first trace those paths and inspect existing tests, then exercise uncertain runtime behavior. (changes: Risk mitigation and early verification priorities.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] After identifying the existing API consumers and entry points, how can a consumer observe imported tickets and requester notifications? (changes: The end-to-end acceptance checks.)
- Q2 [K2] After inspecting the README, API, CLI, and existing tests, which existing behaviours and contracts must the import preserve? (changes: The implementation boundary and regression checks.)
- Q3 [K3] After tracing POST /tickets and the server's routing and error handling, what are the exact ticket fields, validation rules, response and error shapes, and route-matching constraints? (changes: Import validation, routing, error responses, and contract tests.)
- Q4 [K4] After inspecting existing request parsing and validation conventions, how should missing or non-array tickets, an empty array, malformed JSON, and more than 5000 items be handled? (changes: Boundary responses and tests.)
- Q5 [K5] After tracing ticket storage, ID allocation, and notification delivery, what state and side effects occur during creation, who can observe them, and what happens on failure, concurrent requests, or restart? (changes: Atomicity design, side-effect ordering, and failure and concurrency tests.)
- Q6 [K5] After discovery establishes existing notification and storage failure behaviour, what should happen if a valid import encounters a recording or notification failure partway through? (changes: Failure semantics and recovery tests.)
- Q7 [K6] After inspecting package metadata, runtime configuration, and deployment files, what Node.js versions, environment settings, and dependency constraints apply? (changes: Compatible implementation and test commands.)
- Q8 [K7] After tracing the server and CLI, which existing seams allow validation, recording, and notification to be reused while keeping the new behaviour testable? (changes: Module structure and isolation of tests.)
- Q9 [K8] After inspecting test/ and package scripts, how do the existing node:test tests start the service, observe storage and notifications, and clean up? (changes: New boundary tests and their execution.)
- Q10 [K9] After inspecting repository and environment configuration, where is the service run or released, and what access is available for delivery? (changes: Delivery and verification steps.)
- Q11 [K10] After establishing the service's runtime, realistic ticket payloads, and notification path, can a 5000-ticket import complete within 10 seconds at the HTTP boundary? (changes: Performance design and acceptance verification.)
- Q12 [K11] After tracing request size limits, storage, and notification costs, which existing constraints could prevent atomic imports or the 10-second response? (changes: Early risk checks and implementation choices.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.