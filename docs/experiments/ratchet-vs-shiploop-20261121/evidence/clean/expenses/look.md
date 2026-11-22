# Shortfalls

I ran the six delivered tests and exercised the HTTP service on Node v26.12.1. Equal-split remainders, exact splits with omitted and zero shares, settlement order, and single-process concurrent writes through a restart worked as requested. Moving the storage directory away produced a 500 on write. After restoring it, retrying succeeded without a skipped expense number.

To reproduce from the repository root, create a scratch directory with `review_dir=$(mktemp -d "$PWD/../tmp/expense-look.XXXXXX")`. For each run, start `PORT=49371 DATA_FILE="$review_dir/<file>" node server.js &` and record the PID with `pid=$!`. Use a second free port, such as 49372, where indicated. Stop each instance with `kill "$pid"` and `wait "$pid"` before reusing its port. The POST bodies below are literal JSON sent with `Content-Type: application/json`.

### Fractional cents are silently recorded as whole cents (high)

The service needs to reject fractional totals and invalid exact shares before they affect the ledger. Start with a new `inputs.json` and POST `{"id":"trip","members":["Ada","Bo"]}` to `/groups` (201). Send these bodies as raw text to `POST /groups/trip/expenses` in order.

| Request body | Actual response |
| --- | --- |
| `{"payer":"Ada","cents":1.0000000000000001,"split":"equal"}` | 201 `{"expense":1}` |
| `{"payer":"Ada","cents":1,"split":"exact","shares":{"Bo":0.99999999999999999}}` | 201 `{"expense":2}` |
| `{"payer":"Ada","cents":1,"split":"exact","shares":{"Bo":1,"Ada":-1e-400}}` | 201 `{"expense":3}` |

`GET /groups/trip/balances` then returns 200 with `{"Ada":2,"Bo":-2}`. Each POST should return 400 without advancing the expense number, and the balances should still be `{"Ada":0,"Bo":0}`. Parsing the submitted numbers into JavaScript numbers rounds them before validation.

### Two instances can lose an acknowledged expense (high)

An operator starting a replacement process while the old one still runs needs the ledger to preserve accepted expenses or the service to refuse a second writer. The builder specification assumes one process owns each data file. [Builder specification](spec.md#r-6--concurrent-writes)

1. Start instance A with a fresh `ledger.json` and POST `{"id":"trip","members":["Ada","Bo"]}` to `/groups` (201). Start B on port 49372 with the same `DATA_FILE` while A is still listening.
2. Concurrently POST `{"payer":"Ada","cents":3,"split":"exact","shares":{"Bo":3}}` to A and `{"payer":"Ada","cents":5,"split":"exact","shares":{"Bo":5}}` to B, both at `/groups/trip/expenses`. Each returns 201 with `{"expense":1}`.
3. Stop both PIDs, start one instance with the same file, and GET `/groups/trip/balances`. I received 200 with `{"Ada":5,"Bo":-5}`. POST `{"payer":"Ada","cents":1,"split":"exact","shares":{"Bo":1}}` and it returns 201 with `{"expense":2}`. With both original POSTs acknowledged, the restart should show `{"Ada":8,"Bo":-8}` and the next expense should be 3.

### A write through a symlink splits the ledger (high)

An operator using a symlink for `DATA_FILE` needs reads and writes to use the same ledger. A successful write through the alias should still be visible when the operator opens the target directly.

1. Start with a new `primary.json`, POST `{"id":"trip","members":["Ada","Bo"]}` to `/groups` (201), and stop the process.
2. Run `ln -s primary.json "$review_dir/current.json"`. Start with `DATA_FILE="$review_dir/current.json"` and POST `{"payer":"Ada","cents":2,"split":"exact","shares":{"Bo":2}}` to `/groups/trip/expenses`. It returns 201 with `{"expense":1}`, and GET `/groups/trip/balances` returns 200 with `{"Ada":2,"Bo":-2}`.
3. Stop the process and run `test -L "$review_dir/current.json"`. It exits 1 because the write replaced the link with a regular file. Restart using `primary.json` and GET the same balances. It returns 200 with `{"Ada":0,"Bo":0}`. The alias should still resolve to the target and the target should show `{"Ada":2,"Bo":-2}` after the acknowledged write.

### Some successfully created groups are unusable through normal URLs (medium)

Clients need to use the group ID returned on creation in subsequent expense, balance, and settlement URLs. Start with a new file and POST each literal body in the table to `/groups`. Each returns 201 and echoes the ID. Using Node's `fetch` with `http://127.0.0.1:49371` and the paths below gives these results.

| Request body | GET paths | Actual response |
| --- | --- | --- |
| `{"id":".","members":["Ada","Bo"]}` | `/groups/./balances`, `/groups/%2E/balances` | 404 `{"error":"Group not found"}` |
| `{"id":"..","members":["Ada","Bo"]}` | `/groups/../balances`, `/groups/%2E%2E/balances` | 404 `{"error":"Route not found"}` |
| `{"id":"\ud800","members":["Ada","Bo"]}` | `/groups/%ED%A0%80/balances`, `/groups/%EF%BF%BD/balances` | 400 `{"error":"Invalid group ID encoding"}`, then 404 `{"error":"Group not found"}` |

For IDs the service accepts, the fresh group should return 200 with `{"Ada":0,"Bo":0}` through an ordinary URL. An ID that cannot be addressed should receive 400 on creation. Node's URL parser normalizes dot segments even when percent-encoded. A raw HTTP path can reach the dot IDs. The isolated surrogate in the third ID has no valid UTF-8 path encoding.

### Startup fails on a newly allocated empty file (low)

An operator who allocates a fresh zero-byte file for the ledger needs to be able to start with an empty group set. Create one with `empty_file=$(mktemp "$review_dir/empty.XXXXXX")` and run `PORT=49371 DATA_FILE="$empty_file" node server.js`. The process exits 1 with `SyntaxError: Unexpected end of JSON input` before listening. With a newly allocated file, it should listen and return 404 for GET `/groups/trip/balances` until that group is created. A path that does not yet exist already works for first startup.

## Choices the customer was not told

- Duplicate members. Repeated names collapse to one member at their first occurrence.
- ID and name handling. IDs and names must contain some non-whitespace text and are matched literally, preserving case and surrounding whitespace.
- URL format. The group ID occupies one percent-decoded path segment, malformed escapes return 400, and query parameters are ignored.
- Unlisted methods and paths. An unsupported method or unmatched path returns 404, including a trailing slash on a documented balance or settlement path.
- Group creation response. A successful POST returns the ID and the resulting member list. For an existing ID, 409 takes precedence over member validation.
- Request JSON. The service reads JSON without requiring a `Content-Type` header, ignores unused properties such as `shares` on an equal split, and uses the last value when a JSON property is repeated.
- Error responses. The service returns an `{"error":"message"}` object. On a write failure it sends 500 with a generic message, logs the filesystem error to stderr, and leaves the failed change out of the live ledger.
- Amount range. The largest accepted single expense is 9,007,199,254,740,991 cents. The next whole cent returns 400.
- Large totals. Balance and settlement amounts are emitted as exact JSON numbers even above JavaScript's safe-integer range. Clients need a lossless JSON parser to read those amounts exactly.
- Startup defaults. If unset, `PORT` defaults to 3000 and `DATA_FILE` to `expenses.json` relative to the working directory.
- Storage creation and access. A missing data file is created on the first successful mutation. Each write replaces the file with a new file created with owner-only read and write permissions.
