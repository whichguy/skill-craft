You classify the questions that the first planning stage of a software-delivery run asked about a request to change an
existing system. For each question decide one class, by this rule only:

RUNTIME: settling it reliably needs the existing system observed while it runs: how fast or how much it handles, what it
keeps across a restart, a crash or a concurrent change, the exact output, order or shape it produces, or which of
conflicting sources (its code, its documents, its tests) holds.
NOT_RUNTIME: anything else: intent or policy the request leaves open, structure or conventions read from the code, the
delivery, or a decision only a person can make.

Judge each question on its own text. You are not told how anyone proposed to answer it, and the outputs are unlabeled.

Context: The repository exists: an existing Node.js project; the next stage (discovery) will inspect it.

The request:
----- BEGIN REQUEST -----
This directory is an existing Node.js project with no npm dependencies (README.md describes it): an in-memory user store and its HTTP server, src/server.js, which `npm start` runs on the port in the PORT environment variable. Extend the server's user listing, GET /users, with filtering and pagination. The `name` query parameter keeps only the users whose name contains it as plain text, ignoring case; an empty `name` keeps every user. The `page` and `size` query parameters ask for one page of those users in id order, page 1 holding the first `size` of them. When either is given, the answer is a JSON object with "page", "size", "total" (how many users matched), "pages" (how many pages they fill, 0 when none matched) and "items" (the users on that page); `size` is 10 when only `page` is given and `page` is 1 when only `size` is given, and a page after the last one answers an empty "items". `page` must be a whole number of at least 1 and `size` a whole number from 1 to 100: any other value, an empty one included, answers HTTP 400 with a JSON object whose "error" says what is wrong. Keep the API compatible: without `page` and `size`, GET /users still answers a JSON array of users in id order (every user unless `name` is given), any other query parameter is ignored, and GET /users/:id is unchanged. Everything the project already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.
----- END REQUEST -----

===== OUTPUT O1 =====
- Q1 [K1] How do existing clients reach the server and observe its current GET /users response? (changes: The boundary at which the listing behaviour is verified.)
- Q2 [K2] What existing routes and behaviours must the unchanged tests preserve? (changes: Compatibility checks and the implementation scope.)
- Q3 [K3] How does the server parse repeated query parameters, and what response conventions does it already use? (changes: Handling of repeated name, page, and size values and the error response.)
- Q4 [K4] What numeric syntax and id comparison does the existing project use? (changes: Validation and ordering decisions and their edge-case tests.)
- Q5 [K5] How is the in-memory store shared and mutated during requests, and what ordering or isolation does it already provide? (changes: How filtering, totals, and page items are read consistently.)
- Q6 [K6] Which Node.js version, configuration, and npm scripts does the project support? (changes: Compatible language features and the commands used to run and test the server.)
- Q7 [K7] What existing server and store seams support testing the listing without changing unrelated behaviour? (changes: The placement and isolation of filtering and pagination logic.)
- Q8 [K8] How do existing node:test tests start the server, manage store state, and run through npm test? (changes: Test setup and checks at the HTTP boundary.)
- Q9 [K9] Does the repository describe any delivery target beyond the requested project checkout? (changes: The delivery location and any required access or release step.)
- Q10 [K10] Are there existing runtime or response constraints relevant to listing users? (changes: The implementation and verification of applicable performance or security constraints.)
- Q11 [K11] Do the current tests pass, and are there existing ordering or query-handling assumptions that could make the change incompatible? (changes: Risk assessment and the checks used to detect regressions early.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] How do existing clients reach the server, and what response conventions must the listing retain? (changes: The HTTP boundary checks and any response conventions needed for compatibility.)
- Q2 [K2] Which existing routes, store behaviours, and tests must remain intact? (changes: The compatibility boundary and regression checks.)
- Q3 [K3] What are the existing user shape, ID representation, response headers, and error conventions? (changes: Response construction, ID ordering, error formatting, and HTTP tests.)
- Q4 [K4] How should repeated parameters, non-decimal numeric spellings, and values beyond safe integer precision be handled? (changes: Query parsing and invalid-input tests.)
- Q5 [K4] What existing name and ID representations determine case-insensitive substring matching and ID order? (changes: Filtering and sorting decisions and their edge-case tests.)
- Q6 [K5] How is the in-memory store accessed and changed, and what does the runtime already provide for identity, visibility, and concurrent requests? (changes: How a listing reads current state and which state and compatibility checks are appropriate.)
- Q7 [K6] Which Node.js version, scripts, configuration, and dependency constraints does the project use? (changes: Compatible implementation and commands for running and testing it.)
- Q8 [K7] What existing routing and store seams support the change while preserving other behaviour? (changes: The location and isolation of the implementation.)
- Q9 [K8] How are node:test tests organized and how can HTTP responses be checked through the real server boundary? (changes: Test placement, setup, assertions, and verification commands.)
- Q10 [K9] What checkout and execution environment will the next stages use, and is any release target named? (changes: Delivery and access steps.)
- Q11 [K10] Do existing project constraints impose relevant security or performance bounds on this endpoint? (changes: Implementation constraints and checks.)
- Q12 [K11] Where might existing behaviour or tests conflict with the requested ordering, filtering, or pagination contract? (changes: The implementation approach and early regression checks.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do clients currently reach and observe GET /users, including its response headers and user representation? (changes: The boundary-level implementation and tests.)
- Q2 [K2] Which existing routes and behaviors must the change preserve? (changes: Regression checks and the implementation boundary.)
- Q3 [K3] How are query strings and errors currently parsed and serialized, including repeated parameters? (changes: Parameter handling, error messages, and contract tests.)
- Q4 [K4] Which textual forms should count as whole-number page and size values? (changes: Validation and invalid-input tests.)
- Q5 [K5] How does the existing store assign and order IDs, and what state and lifecycle does the runtime already provide? (changes: Ordering, pagination, and state-related tests.)
- Q6 [K6] Which Node.js versions, scripts, configuration, and dependency constraints does the project actually declare? (changes: Compatible implementation and test commands.)
- Q7 [K7] What existing server and store seams permit the listing behavior to be changed and tested in isolation? (changes: Module placement and test setup.)
- Q8 [K8] How are existing node:test tests organized and how does npm test discover and run them? (changes: Test placement, fixtures, and verification.)
- Q9 [K9] What checkout and delivery mechanism does the harness provide for returning changes to this project? (changes: The final delivery step and required access.)
- Q10 [K11] Do existing tests or implementation conventions expose compatibility risks for filtering, ID ordering, or pagination? (changes: Early regression checks and test cases.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] How do existing clients reach the listing and what response conventions do they rely on? (changes: Compatibility checks and the observable HTTP tests.)
- Q2 [K2] What existing server and store behavior must remain intact? (changes: Implementation boundaries and regression coverage.)
- Q3 [K3] How does the server currently parse query strings and format JSON responses and errors? (changes: Query handling, response headers, and error integration.)
- Q4 [K4] How should repeated parameters, numeric spellings, and values beyond safe integer precision be handled? (changes: Validation rules and edge-case tests.)
- Q5 [K4] What case-insensitive substring behavior should apply to names beyond basic text? (changes: Matching implementation and Unicode edge-case tests.)
- Q6 [K5] How is the in-memory user state shared, ordered, and reset, and are there existing visibility or concurrent-change rules? (changes: Where filtering reads data and how state and ordering are tested.)
- Q7 [K6] Which Node.js versions, scripts, configuration, and dependency constraints does the project establish? (changes: Compatible implementation syntax and test commands.)
- Q8 [K7] Which existing server and store seams support isolated changes and HTTP-level testing? (changes: Placement of filtering, pagination, and test setup.)
- Q9 [K8] How do existing node:test tests start the server, isolate data, and run through npm test? (changes: Test setup and verification at the HTTP boundary.)
- Q10 [K9] What checkout and runtime access are available for implementing and verifying the change? (changes: Delivery and verification steps.)
- Q11 [K10] Are there documented performance, security, or other quality constraints governing this endpoint? (changes: Implementation bounds and applicable checks.)
- Q12 [K11] What existing assumptions could make filtering, pagination, or compatibility fail? (changes: Early risk checks and regression tests.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.