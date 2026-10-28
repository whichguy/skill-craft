# node-base: baseline specification

Baseline coverage: deep: src/server.js, src/users.js, src/paginate.js, test, package.json; overview: src/strings.js, README.md, .gitignore; not inspected: none. As of cc92991f2e24.

## Overview

Purpose: node-base keeps a fixed, in-memory set of three users and serves them read-only over HTTP. It also holds two standalone helper modules, text helpers and list paging, which the server does not use. It is deliberately tiny and dependency-free, and its package description calls it the starting point of ShipLoop's step-slice cases, so it is a fixture and not a deployed service. Sources: `README.md:3`; `README.md:7`; `README.md:8`; `package.json` `description`.

Consumers:
- HTTP clients that can reach the server's port: read-only listing and single-user lookup (R-1, R-2). `src/server.js` `createServer`
- Developers and tests that load the modules in-process, through the exports under Entry points.
- ShipLoop cases that start from this project. `package.json` `description`

Entry points:
- Start command: runs the server on the port in PORT, 3000 by default (R-6). `package.json` `scripts`
- Test command: runs every test file with the built-in runner (R-10). `README.md:10`
- In-process exports: `src/server.js` `createServer`; `src/users.js` `getUser`, `listUsers`; `src/paginate.js` `paginate`; `src/strings.js` `capitalize`, `truncate`.

Areas of the census map, one line each:
- **src**: deep for server.js, users.js and paginate.js (R-1 to R-9, AD-1 to AD-12). Overview for strings.js: two text helpers, capitalize and truncate, called only by their own test and untouched by the request. `src/strings.js` `truncate`
- **test**: deep. Seven tests in four files, one file per source module; they are the regression contract and the place for new tests (R-10). `test/server.test.js` "GET /users/:id returns the user or 404"
- **(root)**: deep for package.json, which holds the commands, the runtime range and the module type (R-6, R-10). Overview for README.md, a module list plus the test command, and for .gitignore, which ignores node_modules only. `.gitignore` `node_modules/`

Touched by the request, which extends the user listing with name filtering and paging: src/server.js for the /users route, src/users.js for the data that is filtered and paged, src/paginate.js as the existing paging helper, test for new tests beside the existing seven, and package.json for the test and start commands. Direct interfaces: GET /users and GET /users/:id over HTTP, the PORT variable, and the exports createServer, getUser, listUsers and paginate. The requested behaviour is not specified here; the spec stage measures its changes from this baseline.

Repository records: README.md is the only documentation or instruction file. There is no contributing, agent or security file, no decision record and no contract such as an API schema. Nothing in README.md restricts automated or generated changes or the requested work. README.md documents no route, port or start command, so the HTTP contract below rests on the code and on one test. Linked, not copied: `README.md`.

Evidence: discovery's baseline run of the suite executed 7 tests, with 7 passed, 0 failed and exit 0. A tested source below means a named test among those 7 asserts it. Code comments are cited as stated intent only where an entry says stated or conflict; otherwise the code itself is the observation. Every source file and test file was read in full, and the git history is a single commit.

## Requirements

### R-1 User listing
Status: baseline · Source: observed (`src/server.js` `createServer`); observed (`src/users.js` `USERS`); documented (`README.md:8`) · As of: cc92991f2e24
- GET /users answers HTTP 200 with a JSON array holding every user in ascending id order, today ids 1, 2 and 3 (`src/server.js` `createServer`; `src/users.js` `listUsers`)
- Each element is a user object with exactly the properties id, a number, then name and email, strings, in that order (`src/users.js` `USERS`)
- The query string is never read: any query parameter, known or not, leaves the answer unchanged, and only the method and the path pick the route (`src/server.js` `createServer`)
- Only the exact path /users with method GET is the listing: a trailing slash, another letter case or any other method gets the generic not-found error of R-3 (`src/server.js` `createServer`)
- Not covered by any test over HTTP: the only server test requests /users/:id, and the store-level test asserts only that 3 users are listed (`test/server.test.js` "GET /users/:id returns the user or 404")

### R-2 Single-user lookup
Status: baseline · Source: observed (`src/server.js` `createServer`); tested (`test/server.test.js` "GET /users/:id returns the user or 404") · As of: cc92991f2e24
- GET /users/:id, where id is one or more decimal digits with nothing after them, answers 200 with that user's object, the same properties as a listing element, when a user has that id (`test/server.test.js` "GET /users/:id returns the user or 404")
- When no user has the id the answer is 404 with the not-found error of R-3, and id 42 is the tested case (`test/server.test.js` "GET /users/:id returns the user or 404")
- The digits are read as a number, so leading zeros name the same user, /users/01 being user 1, and /users/0 is not found (`src/server.js` `createServer`)
- An id with anything other than digits, such as a sign, a decimal point, letters, nothing at all or a trailing slash, is not this route and gets the generic not-found error (`src/server.js` `createServer`)
- The query string is ignored and only GET is served; any other method is not found (`src/server.js` `createServer`)

### R-3 Answer format and error reporting
Status: baseline · Source: observed (`src/server.js` `send`); observed (`src/server.js` `createServer`); tested (`test/server.test.js` "GET /users/:id returns the user or 404"); inferred (`src/server.js` `createServer`) · As of: cc92991f2e24
- Every answer is compact JSON text sent with the header content-type: application/json, no charset, and the code sets no other header (`src/server.js` `send`)
- An error answer is a JSON object whose only property is error, holding a fixed text; the one error in use is not found with HTTP 404, whose status is tested for an unknown user (`test/server.test.js` "GET /users/:id returns the user or 404")
- Any request other than GET of /users or of /users/:id, whether another path or another method with HEAD and POST included, gets that same 404 answer; the server's own code answers only 200 and 404 (`src/server.js` `createServer`)
- No part of the request is echoed into an answer, because error texts are constants (`src/server.js` `createServer`)
- Inferred, not run: a failure raised while a request is handled is not caught, so it yields no JSON error and, as an unhandled exception, would stop the whole process, for example a request target the URL parser rejects (`src/server.js` `createServer`)

### R-4 User store and persistence
Status: baseline · Source: observed (`src/users.js` `USERS`); tested (`test/users.test.js` "getUser finds a user by id and returns null otherwise"); tested (`test/users.test.js` "listUsers returns every user"); documented (`README.md:7`) · As of: cc92991f2e24
- The store holds exactly three users fixed in the source: 1 Ada Lovelace, 2 Grace Hopper and 3 Alan Turing, with the addresses ada@example.com, grace@example.com and alan@example.com (`src/users.js` `USERS`)
- Looking a user up by number returns that user, or null when none has the number (`test/users.test.js` "getUser finds a user by id and returns null otherwise")
- Listing returns all users in ascending id order, which is the stored order because nothing sorts; the count 3 is pinned by a test, so adding a stored user breaks an existing test (`test/users.test.js` "listUsers returns every user")
- Each listing is a new list, so reordering or trimming it leaves the store alone, but the users inside it and the user a lookup returns are the stored records themselves, so changing one changes the store (`src/users.js` `listUsers`; `src/users.js` `getUser`)
- Nothing creates, changes or deletes a user, and data lives in memory only: every start begins with the same three users and nothing is saved (`src/users.js` `USERS`; `src/server.js` `createServer`)

### R-5 Paging of a list
Status: baseline · Source: observed (`src/paginate.js` `paginate`); tested (`test/paginate.test.js` "paginate returns the requested page of an evenly divided list"); tested (`test/paginate.test.js` "paginate rejects a bad page size"); documented (`README.md:6`); conflict (`src/paginate.js` `paginate` vs `README.md:6`) · As of: cc92991f2e24
- Inputs are a list, a page number counted from 1 and a page size; none has a default, and an omitted one counts as invalid (`src/paginate.js` `paginate`)
- The result is an object with exactly three properties: page, the number asked for; pages, the page count; and items, the entries on that page in the list order. It carries neither the page size nor the list length, and the existing test compares with strict deep equality, so an extra property would fail it (`test/paginate.test.js` "paginate returns the requested page of an evenly divided list")
- For a list that divides evenly, 6 entries at size 3, the result is right: page 1 holds entries 1 to 3, page 2 holds entries 4 to 6, and pages is 2 (`test/paginate.test.js` "paginate returns the requested page of an evenly divided list")
- The page count is the list length divided by the size, rounded down, so a trailing partial page is never counted or returned: 7 entries at size 3 give pages 2, and entry 7 is unreachable (`src/paginate.js` `paginate`)
- A list shorter than the size has 0 pages and every page is empty: the 3 stored users at size 10 give pages 0 and no items, and at size 2 give pages 1 with user 3 unreachable (`src/paginate.js` `paginate`)
- A page number above the page count answers empty items and not an error (`src/paginate.js` `paginate`)
- Invalid input is rejected by throwing, checked in this order: not a list is a type error; a size that is not a whole number of at least 1 is a range error saying size must be a positive integer; a page failing the same test is a range error saying page must be a positive integer. With both bad, the size error wins. There is no upper limit on size, and numeric text such as 2 is invalid because only real numbers pass. Only a size of 0 is tested (`src/paginate.js` `RangeError`; `test/paginate.test.js` "paginate rejects a bad page size")
- The input list is left unchanged and items is a new list (`src/paginate.js` `paginate`)
- No source file calls the helper today: the server's only local import is the user store (`src/server.js` `./users`)
- Conflict: the README says the helper splits a list into pages and its doc comment promises the page count, yet a list that does not divide evenly loses its last partial page; the current behaviour stands until the request or the owner decides (`src/paginate.js` `paginate`; `README.md:6`)

### R-6 Server start and configuration
Status: baseline · Source: observed (`src/server.js` `PORT`); observed (`package.json` `scripts`); observed (`package.json` `engines`) · As of: cc92991f2e24
- The start command runs the server on the port in the PORT environment variable; when PORT is unset, empty, 0 or not a number, the port is 3000 (`src/server.js` `PORT`; `package.json` `scripts`)
- Once the server is accepting connections it writes one line, listening on followed by the port, to standard output, and then serves until the process is stopped (`src/server.js` `listening on`)
- No address is given, so the server accepts connections on all of the machine's network interfaces (`src/server.js` `listen`)
- Loading the server code never starts listening: a caller that builds a server chooses the port and address, and the tests use an ephemeral port on 127.0.0.1 (`src/server.js` `require.main`; `test/server.test.js` `withServer`)
- No other setting exists: no configuration file, no command-line flag and no other environment variable is read (`src/server.js` `PORT`)
- The declared minimum runtime version is 20 (`package.json` `engines`)

### R-7 Background work
Status: baseline · Source: observed (`src/server.js` `createServer`); observed (`test/server.test.js` `withServer`); inferred (`src/server.js` `require.main`) · As of: cc92991f2e24
- Nothing runs apart from answering requests: there are no timers, queues, workers, watchers, start-up tasks or scheduled jobs, and each request is answered from memory while it is handled (`src/server.js` `createServer`; `src/users.js` `USERS`)
- No signal or shutdown handling is installed; inferred, not run: stopping the process ends in-flight requests with the runtime's default behaviour (`src/server.js` `require.main`)
- The tests close the server they start, so the test process can finish (`test/server.test.js` `withServer`)

### R-8 Identity and access
Status: baseline · Source: observed (`src/server.js` `createServer`) · As of: cc92991f2e24
- No credential is asked for or checked: there is no login, session, token, role or per-user permission, and every caller that can reach the port may use every route (`src/server.js` `createServer`)
- Only the request's method and target decide the answer; headers, cookies, the caller's address and any body are never read (`src/server.js` `createServer`)

### R-9 Privacy and security
Status: baseline · Source: observed (`src/server.js` `createServer`); observed (`src/server.js` `send`); observed (`src/users.js` `USERS`) · As of: cc92991f2e24
- Every answer that carries a user carries all of that user's properties, email included, with no field selection, masking or per-caller filtering (`src/server.js` `send`; `src/users.js` `USERS`)
- The stored records are fixed example data with addresses under example.com, and the repository's tracked files hold no credential or secret (`src/users.js` `USERS`)
- Plain HTTP only: the server sets no TLS, CORS, caching or other security header and applies no rate limit, size limit or timeout of its own beyond the runtime's defaults (`src/server.js` `send`)
- Request data reaches the code only as the method and the URL target, the id is limited to digits by an anchored pattern, and the only log line is the start-up line (`src/server.js` `createServer`)

### R-10 Test suite and commands
Status: baseline · Source: documented (`README.md:10`); observed (`package.json` `scripts`); tested (`test/server.test.js` "GET /users/:id returns the user or 404"); tested (`test/paginate.test.js` "paginate returns the requested page of an evenly divided list"); inferred (`package.json` `scripts`) · As of: cc92991f2e24
- The test command runs the platform's built-in runner with no file list, and the baseline run found the seven existing tests in the four test files under test (`README.md:10`; `package.json` `scripts`)
- Inferred: a new file under test named with the .test.js ending is found by the same file discovery and runs with the existing tests (`package.json` `scripts`)
- Over real HTTP, user 1 is Ada Lovelace with status 200 and id 42 gives 404 (`test/server.test.js` "GET /users/:id returns the user or 404")
- Looking up user 2 gives Grace Hopper and user 99 gives null (`test/users.test.js` "getUser finds a user by id and returns null otherwise")
- The store lists 3 users (`test/users.test.js` "listUsers returns every user")
- Paging 1 to 6 at size 3 gives page 1 with pages 2 and items 1 to 3, and page 2 with pages 2 and items 4 to 6, compared with strict deep equality (`test/paginate.test.js` "paginate returns the requested page of an evenly divided list")
- Paging with a size of 0 is rejected as a range error (`test/paginate.test.js` "paginate rejects a bad page size")
- The text helpers keep their tested results: hello becomes Hello, the empty text stays empty, short text is kept, long text is cut with an ellipsis, and a maximum of 0 is rejected as a range error (`test/strings.test.js` "capitalize upper-cases the first character"; `test/strings.test.js` "truncate keeps short text and cuts long text with an ellipsis")
