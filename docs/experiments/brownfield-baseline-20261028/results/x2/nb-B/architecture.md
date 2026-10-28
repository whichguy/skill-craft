# node-base: baseline architecture

As of cc92991f2e24. This file records what exists and proposes no change.

## Stack

- Language and modules: JavaScript as CommonJS modules in strict mode. `package.json` `type`
- Runtime: Node.js 20 or newer, as declared. `package.json` `engines`
- Dependencies: none. The code uses only built-ins: node:http, node:test, node:assert/strict, and the global fetch and URL. `package.json` `description`; `src/server.js` `node:http`
- Data: one in-memory array; no database, file or network storage. `src/users.js` `USERS`
- Commands: npm scripts for test and start only; no build, bundling or transpilation step. `package.json` `scripts`
- Package: private, version 1.0.0, with no lockfile tracked. `package.json` `private`

## Structure

- src/server.js: the HTTP surface. It owns routing, every answer, and the process entry that reads the port and starts listening. `src/server.js` `createServer`
- src/users.js: the user data and its two read functions. `src/users.js` `USERS`
- src/paginate.js: the list paging helper; the server does not call it today. `src/paginate.js` `paginate`
- src/strings.js: two text helpers that the server does not call; overview only. `src/strings.js` `truncate`
- test: one test file per source module; the regression contract and the place for new tests. `test/users.test.js` `../src/users`
- root: package.json owns the commands, the runtime range and the module type; README.md lists the modules and the test command; .gitignore ignores node_modules. `README.md:5`

## Conventions

- Instruction files: README.md is the only one, linked and not copied here. It lists the four modules and the test command and sets no rule on the work. No contributing, agent or security file and no decision record exists. `README.md:5`
- Linters, formatters and checks: none configured. package.json defines only the test and start commands, and no lint, format, type-check, hook or CI file is tracked, so style is kept by hand. `package.json` `scripts`
- Source style, the same in every source and test file: the strict-mode directive first, 2-space indent, single quotes, semicolons, const bindings and arrow callbacks. Every source file puts a doc comment above each exported function and ends with one module.exports object; built-ins are required with the node: prefix and local files by relative path. `src/paginate.js` `use strict`, `module.exports`
- Naming: camelCase functions, one lower-case file per concept in src, and a test file named after its module as the module name followed by .test.js. `test/users.test.js` `../src/users`
- Argument checking in helpers: done up front, with the text or list checked before the numbers; a bad type throws a type error and a bad number throws a range error, with a message of the form the argument name, must be, and the rule; the caller gets the exception and no value. `src/strings.js` `truncate`
- HTTP routes: build a URL from the request target, branch on method and pathname, call the user store, and answer through send, with a constant error text on failure. The single-user route is the pattern for a route, and no handler catches errors. `src/server.js` `createServer`
- Number parsing precedent: the only numeric conversions are the permissive conversion of PORT with a fallback of 3000 and the digits-only id pattern; nothing in the repository parses a query value. `src/server.js` `PORT`
- Tests: built-in runner with strict assertions; one test per behaviour, named as a sentence; helpers stay local to the test file that uses them, as withServer does in the server test; server tests use real HTTP on an ephemeral 127.0.0.1 port and close the server in a finally block; the paging test compares whole results with strict deep equality. `test/server.test.js` `withServer`
- Features most like the request: the single-user route, a second branch in the same listener, answered through send and tested over real HTTP, and the paging helper, which validates its arguments and has its exact result shape pinned by a test. `test/server.test.js` "GET /users/:id returns the user or 404"; `test/paginate.test.js` "paginate returns the requested page of an evenly divided list"

## Interfaces and boundaries

- Inbound HTTP, the only external interface: GET /users and GET /users/:id; every other request answers 404. The contract is R-1 to R-3 in the specification. `src/server.js` `createServer`
- Process: the start command, the PORT variable and one start-up line on standard output (R-6). `src/server.js` `PORT`
- In-process exports, relied on by the tests: `src/server.js` `createServer` returns a server that is not listening; `src/users.js` `getUser` returns a stored user or null; `src/users.js` `listUsers` returns a new list of stored users; `src/paginate.js` `paginate` returns the page object or throws; `src/strings.js` `capitalize` and `src/strings.js` `truncate` return text or throw.
- Dependency direction: the server depends on the user store alone; the paging helper and the text helpers are leaves that no source file uses; each test depends on its module, and the server test reaches the server only over HTTP. `src/server.js` `./users`
- Outbound: none. The code makes no network call and uses no file system, database or child process; its only side effects are the answer, the start-up log line and the listening socket. `src/server.js` `createServer`
- Trust boundary: the request method and target are the only external input, they are handled as untrusted text and never echoed, and no authentication stands behind the boundary (R-8, R-9). `src/server.js` `createServer`

## Decisions

- AD-1 (inherited) The project depends on nothing beyond the runtime's built-ins: node:http for serving, node:test and node:assert/strict for tests, plus the global fetch and URL; there is no dependency list, lockfile or install step. Why: the README opens by calling it a project with no dependencies, and the package description says dependency-free (stated: `README.md:3`). Evidence: `package.json` `description`; `src/server.js` `node:http`.
- AD-2 (inherited) Source and test files are CommonJS modules in strict mode, each ending with one module.exports object that names its public functions, and built-ins are required with the node: prefix. Why: the package declares the module type and states no reason (inferred). Evidence: `package.json` `type`; `src/users.js` `module.exports`.
- AD-3 (inherited) HTTP routing is hand-written inside the one request listener that createServer builds: it turns the request target into a URL, branches on method and path, with an exact comparison for the list and an anchored pattern for one user, and ends in the not-found answer. Each route is a branch in that listener. Why: the README says the server is built on the built-in HTTP module (stated: `README.md:8`). Evidence: `src/server.js` `createServer`.
- AD-4 (inherited) Every answer goes through one helper, send, which sets only the JSON content type and writes the compact JSON of the body; an error answer is an object with a single error property holding a constant text. Why: one response shape serves every route (inferred). Evidence: `src/server.js` `send`.
- AD-5 (inherited) Failures reach HTTP callers only as that error answer, and only for the one case the code anticipates, not found with status 404. Helper functions instead signal bad arguments by throwing a type error or a range error, and the listener has no try or catch, so a thrown error is not turned into a JSON answer. Why: the repository documents no error policy (inferred). Evidence: `src/paginate.js` `paginate`; `src/strings.js` `truncate`; `src/server.js` `createServer`.
- AD-6 (inherited) State is a module-level constant array of user records in the users module; callers read it only through getUser, which returns the stored record, and listUsers, which returns a new list of the same records; the server never touches the array and no function writes it. Why: the README calls it an in-memory user store (stated: `README.md:7`). Evidence: `src/users.js` `USERS`.
- AD-7 (inherited) The one configuration value, the listening port, is read from the PORT environment variable once, inside the block that runs only when the server file is the program entry, with a fallback of 3000; modules read no environment when loaded and createServer takes no options. Why: loading the server for tests must not bind a port (inferred). Evidence: `src/server.js` `require.main`.
- AD-8 (inherited) Building a server and listening are separate steps: createServer returns a server that is not listening, and the caller picks the port and address. Tests start it on an ephemeral port on 127.0.0.1, call it over real HTTP with the global fetch and close it in a finally block; nothing is mocked. Why: the code comment says the server is not listening until the caller calls listen (stated: `src/server.js` `createServer`). Evidence: `test/server.test.js` `withServer`.
- AD-9 (inherited) Tests use the runtime's built-in runner with strict assertions; each source module has a matching test file named after it; the test command is the runner's own file discovery with no configuration; test names are sentences that state the behaviour. Why: the README gives the test command as the runner (stated: `README.md:10`). Evidence: `package.json` `scripts`; `test/users.test.js` "listUsers returns every user".
- AD-10 (inherited) Requests are answered synchronously from memory in the listener that receives them; there are no timers, queues, workers or shutdown hooks, so no background work exists to coordinate with. Why: nothing in the repository starts such work (inferred). Evidence: `src/server.js` `createServer`.
- AD-11 (inherited) There is no identity or access layer: the listener looks only at the method and the path, treats every caller alike and returns stored user records whole, email included. Why: no document states an access policy and the data are fixed example records (inferred). Evidence: `src/server.js` `createServer`; `src/users.js` `USERS`.
- AD-12 (inherited) Helper modules are pure, argument-checking functions that stand alone: the paging helper and the text helpers are not used by the server today and only their tests call them, and the paging helper reports the page, the page count and the items but not the list length or the size. Why: the README lists them as separate modules beside the server and states no use for them (inferred). Evidence: `src/paginate.js` `paginate`; `src/strings.js` `capitalize`; `test/paginate.test.js` "paginate returns the requested page of an evenly divided list".

## Superseded

None. The repository keeps no decision records, so no AD above links one and none is superseded.
