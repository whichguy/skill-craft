# Architecture

## Decisions
AD-1: Use built-in HTTP and filesystem primitives, with a single serialized writer; requests complete after persistent replacement succeeds. A process owns its configured data file.

## Real-boundary checks
Planned: component tests spawn the actual server and issue HTTP requests against fresh local data files. Restart validates disk state; concurrent requests validate serialization. No remote services, UI, cache, identity or async worker exist.

## Structure
AD-2: CommonJS server.js owns HTTP parsing, validation, calculation and single-process JSON file writes. The data file stores groups with ordered members and expenses, local filesystem only; no migration from empty baseline. Data is retained until operator removes the file. Atomic replacement and serialized writes protect accepted changes; errors return failure.

## Interfaces and boundaries
Clients use HTTP request/response. PORT and DATA_FILE select local runtime; no external service or authentication. Each incoming mutation is validated on the server.
