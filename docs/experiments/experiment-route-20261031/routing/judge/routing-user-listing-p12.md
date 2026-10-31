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
- Q1 [K1] How do existing clients and tests exercise the HTTP server and observe its responses? (changes: The boundary-level verification of the listing outcome.)
- Q2 [K2] What existing routes and store behavior must remain compatible, and how are users ordered by id today? (changes: The implementation boundary and regression checks.)
- Q3 [K3] How does the server currently parse query strings and serialize responses, including repeated query parameters? (changes: Query parsing and response contract tests.)
- Q4 [K4] What textual forms and numeric range should count as valid whole-number page and size values, and how should multiple invalid parameters be reported? (changes: Validation rules, error messages, and edge-case tests.)
- Q5 [K4] What case-insensitive plain-text matching convention fits the existing user data and runtime? (changes: Name matching and its edge-case tests.)
- Q6 [K5] How is the in-memory store shared, reset, and accessed during requests, and what existing behavior applies to concurrent changes or restarts? (changes: Test isolation and preservation of store behavior.)
- Q7 [K6] Which Node.js versions, startup configuration, and dependency constraints does the project actually declare? (changes: Compatible implementation syntax and test commands.)
- Q8 [K7] What existing modules or seams support isolated changes and tests without changing public behavior? (changes: Implementation placement and test setup.)
- Q9 [K8] How does npm test discover and run existing node:test tests, and how can the new HTTP outcomes be checked alongside them? (changes: Test file placement, invocation, and boundary assertions.)
- Q10 [K9] What checkout and local runtime access are available for implementing and verifying the change? (changes: The delivery and verification steps.)
- Q11 [K10] Does the project document any applicable performance or security constraints for the existing HTTP API? (changes: Implementation choices and relevant verification.)
- Q12 [K11] Do the existing code, documentation, and tests reveal incompatible assumptions or behavior that could prevent the requested contract? (changes: Risk handling, implementation, and acceptance tests.)
===== END OUTPUT O1 =====

===== OUTPUT O2 =====
- Q1 [K1] How do callers reach the existing server, and how can a test observe the listing through its HTTP boundary? (changes: The integration test setup and observation of GET /users.)
- Q2 [K2] What existing routes and behaviors must remain compatible, and what conventions does the project use for user ordering? (changes: The implementation boundary and regression coverage.)
- Q3 [K3] How are query parameters parsed and errors currently represented, and what should happen when a parameter is repeated? (changes: Parameter parsing and error-response tests.)
- Q4 [K4] Which textual forms count as whole-number page and size values, and how should very large values be handled? (changes: Validation rules and boundary tests.)
- Q5 [K4] What case-insensitive matching convention applies to names? (changes: The matching implementation and non-ASCII test expectations.)
- Q6 [K5] How does the in-memory store represent and update users, and what state is shared across requests or lost on restart? (changes: How the listing reads current users and how its tests isolate state.)
- Q7 [K6] What Node.js version, startup configuration, and dependency constraints does the project actually declare? (changes: Compatible APIs, commands, and test setup.)
- Q8 [K7] Which existing modules or seams support filtering, pagination, and isolated testing without changing unrelated behavior? (changes: The placement and structure of the implementation.)
- Q9 [K8] How are existing node:test tests run and how do they start, observe, and clean up the server? (changes: New tests and the verification command.)
- Q10 [K9] What checkout and execution environment will the next stage use to make and verify the change? (changes: The delivery and verification steps.)
- Q11 [K10] Are there existing performance, security, or response-quality constraints that affect this endpoint? (changes: Implementation choices and any necessary checks.)
- Q12 [K11] Which existing assumptions about ids, user data, or server lifecycle could make the change fail or break compatibility? (changes: Risk-focused implementation and regression tests.)
===== END OUTPUT O2 =====

===== OUTPUT O3 =====
- Q1 [K1] How do existing clients reach the server and observe its current user-listing response? (changes: The boundary used to verify the HTTP outcome.)
- Q2 [K2] What existing routes and behaviours must the compatibility checks preserve? (changes: Regression coverage and implementation boundaries.)
- Q3 [K3] How does the server currently parse query strings and serialize responses, including repeated query parameters? (changes: Query handling and response compatibility tests.)
- Q4 [K4] What numeric syntax and case-insensitive matching conventions does the existing project use? (changes: Validation and filtering edge-case tests.)
- Q5 [K5] How are users stored, identified and ordered, and what state does the server already provide across requests? (changes: Sorting, filtering and pagination decisions and their tests.)
- Q6 [K6] Which Node.js versions, startup configuration and dependency constraints does the project declare? (changes: Compatible implementation and test execution.)
- Q7 [K7] What existing server and store seams support isolated changes and HTTP-level tests? (changes: Where listing logic and tests are placed.)
- Q8 [K8] How do the existing node:test suite and npm test command start, isolate and check the server? (changes: Test setup and verification commands.)
- Q9 [K9] What checkout and runtime configuration are available for delivering and exercising the project? (changes: Delivery and execution steps.)
- Q10 [K11] Do existing tests or implementation assumptions expose compatibility risks around ordering, query parsing or state? (changes: Early regression checks and edge-case coverage.)
===== END OUTPUT O3 =====

===== OUTPUT O4 =====
- Q1 [K1] How does the existing server expose GET /users to HTTP clients, and how can a test observe its response at that boundary? (changes: The test setup and observation of the requested outcome.)
- Q2 [K2] What existing routes and behaviours must remain compatible, including the ordering and representation of users? (changes: The preserved-behaviour checks and implementation boundary.)
- Q3 [K3] How does the current server parse query parameters and format JSON errors, and what happens when a parameter is repeated? (changes: Query parsing, duplicate-parameter handling and error responses.)
- Q4 [K4] Which textual forms count as whole-number query values, and how should case-insensitive name matching be applied when existing conventions do not settle them? (changes: Validation and matching decisions and their edge-case tests.)
- Q5 [K5] How does the store maintain users and id order, and what behaviour does it already provide when state changes during a request or the process restarts? (changes: How the listing reads state and which existing state behaviours tests preserve.)
- Q6 [K6] Which Node.js versions, startup configuration and dependency constraints does the project actually specify? (changes: Runtime-compatible implementation and test commands.)
- Q7 [K7] Where are the existing server and store seams that can support the change without disrupting other behaviour? (changes: The modules changed and how the behaviour is isolated for testing.)
- Q8 [K8] How does npm test discover and run the existing tests, and how are HTTP responses and store fixtures tested? (changes: New node:test coverage and the full verification command.)
- Q9 [K9] What checkout and execution setup does the harness provide for delivering and verifying changes in this project? (changes: The delivery and verification steps.)
- Q10 [K11] Do the existing implementation, documentation and tests disagree about any behaviour that the extension must preserve? (changes: Compatibility decisions and early regression checks.)
===== END OUTPUT O4 =====

Answer with one JSON object only, no prose: {"O1": {"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}, "O2": {...}, ...},
with every output and every question id listed above.