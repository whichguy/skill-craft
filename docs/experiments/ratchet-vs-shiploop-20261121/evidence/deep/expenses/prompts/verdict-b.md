# Three deliveries of one request: which is the better feature?

Three builders each delivered the same customer request (below). Each delivery was audited by running it: every
stated requirement, a list of conditions the request leaves unsaid, its tests, its specification and its documents.
Items the audits disagreed on were run again on all three by another person, and every defect an auditor reported
was tried on all three. You have the audits (with those re-runs applied) and the defect table. The deliveries are
labelled X, Y and Z; the labels and their order carry no meaning. You do not have the products and should not guess
at them beyond the audits.

Judge as the person who will run this feature and keep it working: what does each delivery give that the others do
not, and does it matter? Size is not quality: a longer specification, more tests or more code count only through
what the audits show they bought, and count against a delivery where the audits show they cost (requirements the
customer did not ask for, tests that pin one builder's choices, code a maintainer must carry). Count each
consequence once, however many audit lines mention it.

For each pair (Z-X, Z-Y, Y-X):

- `better`: `<letter>-much`, `<letter>-some` (naming the better delivery) or `same`.
- `advantages`: each real advantage of either side, with the audit line or defect id behind it (`ref`) and whom it
  matters to: `requester`, `operator`, `maintainer` or `no one`.
- `lesser_lacks`: what the lesser delivery would need to match the better one, as a list of concrete changes.
- `one_task_closes`: `yes` if one short follow-up task (about an hour of the same builder's work) would close that
  list, else `no`. `yes` when `better` is `same`.
- `why`: three sentences at most.

Answer with one JSON object and nothing else:

```json
{"pairs": [{"pair": "Z-X", "better": "same", "advantages": [{"of": "X", "what": "...", "ref": "U-4", "matters_to": "operator"}], "lesser_lacks": ["..."], "one_task_closes": "yes", "why": "..."}]}
```

## The request

Build a small shared-expenses service in Node.js (no npm dependencies). server.js listens on the port in the PORT environment variable and keeps its data in the JSON file named by the DATA_FILE environment variable, so groups and expenses survive a restart. POST /groups with {"id": "<group id>", "members": ["<name>", ...]} creates a group: 201, 409 if the id exists, and 400 unless members holds at least two distinct non-empty names. POST /groups/<id>/expenses records an expense paid by one member. {"payer": "<name>", "cents": <positive integer>, "split": "equal"} shares it equally among all members, with any cents left over after an even division going one each to the members listed first. {"payer": "<name>", "cents": <positive integer>, "split": "exact", "shares": {"<name>": <cents>, ...}} makes each member listed in shares owe that many whole cents (zero is allowed), and the shares must add up to cents. It answers 201 with {"expense": <n>}, where n is 1 for the group's first expense, then 2, and so on; 400 for an unknown payer or member, a non-positive or non-integer amount, an unknown split, or shares that do not add up. GET /groups/<id>/balances returns an object with each member's net cents, what they paid minus what they owe, so the balances add up to 0. GET /groups/<id>/settlements returns a JSON array of {"from", "to", "cents"} payments that bring every balance to 0: repeatedly the member who owes most pays the member who is owed most the smaller of the two amounts, and ties go to the member listed first. Every route under /groups/<id> answers 404 for an unknown group. Concurrent requests must never lose an expense. Cover the behaviour with node:test tests under test/ that run with `node --test`.

## The inventory


## Stated requirements

- **S-1**: The service is written in Node.js, with server.js as the server.
- **S-2**: The service uses no npm dependencies.
- **S-3**: server.js listens on the port given in the PORT environment variable.
- **S-4**: The service keeps its data in the JSON file named by the DATA_FILE environment variable.
- **S-5**: Groups survive a restart of the server with the same DATA_FILE.
- **S-6**: Expenses survive a restart of the server with the same DATA_FILE.
- **S-7**: POST /groups with {"id": "<group id>", "members": ["<name>", ...]} creates a group and answers 201.
- **S-8**: POST /groups answers 409 if a group with that id already exists.
- **S-9**: POST /groups answers 400 when members holds fewer than two names.
- **S-10**: POST /groups answers 400 when members holds fewer than two distinct names (for example ["Ann", "Ann"]).
- **S-11**: POST /groups answers 400 when members holds fewer than two non-empty names (for example ["Ann", ""]).
- **S-12**: POST /groups/<id>/expenses records an expense paid by one member, the payer.
- **S-13**: An expense {"payer": "<name>", "cents": <positive integer>, "split": "equal"} is shared equally among all members of the group.
- **S-14**: For split "equal", any cents left over after an even division go one each to the members listed first in the group's members order.
- **S-15**: An expense {"payer": "<name>", "cents": <positive integer>, "split": "exact", "shares": {"<name>": <cents>, ...}} makes each member listed in shares owe that many whole cents.
- **S-16**: For split "exact", a share of zero is allowed.
- **S-17**: For split "exact", the shares must add up to cents.
- **S-18**: A recorded expense answers 201 with {"expense": <n>}.
- **S-19**: The expense number n is 1 for the group's first expense, then 2, and so on.
- **S-20**: POST /groups/<id>/expenses answers 400 for an unknown payer.
- **S-21**: POST /groups/<id>/expenses answers 400 for an unknown member (a name in shares that is not a group member).
- **S-22**: POST /groups/<id>/expenses answers 400 for a non-positive amount.
- **S-23**: POST /groups/<id>/expenses answers 400 for a non-integer amount.
- **S-24**: POST /groups/<id>/expenses answers 400 for an unknown split.
- **S-25**: POST /groups/<id>/expenses answers 400 for shares that do not add up to cents.
- **S-26**: GET /groups/<id>/balances returns an object with each member's net cents.
- **S-27**: A member's net cents are what they paid minus what they owe.
- **S-28**: The balances returned by GET /groups/<id>/balances add up to 0.
- **S-29**: GET /groups/<id>/settlements returns a JSON array of {"from", "to", "cents"} payments.
- **S-30**: The settlement payments bring every balance to 0.
- **S-31**: Settlements are built by repeatedly having the member who owes most pay the member who is owed most the smaller of the two amounts.
- **S-32**: In settlements, ties (between debtors or between creditors) go to the member listed first.
- **S-33**: Every route under /groups/<id> answers 404 for an unknown group.
- **S-34**: Concurrent requests never lose an expense.
- **S-35**: The behaviour is covered by node:test tests under test/ that run with `node --test`.

## Conditions the request leaves unsaid

- **U-1**: What status a request body that is not valid JSON gets, and whether the server keeps serving afterwards.
  - Probe: Start the server. POST /groups with Content-Type application/json and the raw body `{` (and separately `not json`). Create group g with ["Ann","Bob"] and POST /groups/g/expenses with the raw body `not json`. Record each status and body. Then POST a valid new group and GET /groups/g/balances and check both still work.
  - Outcomes that would be acceptable: 400 for each broken body, with or without an error message, is the fitting answer; another 4xx is acceptable. The server must stay up and answer the following valid requests; nothing is stored from the broken body.
- **U-2**: What happens when a required field is missing: an expense without payer, cents or split, split "exact" without shares, or a group without id or members.
  - Probe: Create group g with ["Ann","Bob"]. POST /groups/g/expenses with {}, with {"payer": "Ann", "cents": 100}, with {"cents": 100, "split": "equal"}, with {"payer": "Ann", "split": "equal"}, and with {"payer": "Ann", "cents": 100, "split": "exact"}. POST /groups with {} and with {"id": "h"}. Record each status and body, then GET /groups/g/balances.
  - Outcomes that would be acceptable: 400 for each, with no expense or group stored, and the server still answering. A 500 is a worse fit; a crash is not acceptable.
- **U-3**: Whether JSON values of the wrong type are refused or coerced: cents as a string, members as a string, a member that is not a string, or shares that is not an object.
  - Probe: POST /groups {"id": "g", "members": "Ann,Bob"} and {"id": "g1", "members": ["Ann", 7, "Bob"]}. Create group g2 with ["Ann","Bob"]. POST /groups/g2/expenses with {"payer": "Ann", "cents": "100", "split": "equal"}, with {"payer": "Ann", "cents": 100, "split": "exact", "shares": [100]}. Record each status; for any 201 GET /groups/g2/balances.
  - Outcomes that would be acceptable: 400 for each is fine. Coercing the string "100" to 100 and answering 201 is also fine if consistent. No 500 or crash; splitting the string "Ann,Bob" into members is not required.
- **U-4**: Which group ids are accepted (empty, missing, numeric, containing '/', spaces, '%', unicode), and whether every group that got 201 can then be addressed through /groups/<id>/ by all three group routes, percent-encoded where the path needs it.
  - Probe: Separately POST /groups with valid members and ids "", none, 1, "a/b", "a b", "50%" and "café". For each 201, GET balances and settlements and POST a valid expense at the path formed from the id, percent-encoded where needed (for example /groups/a%20b/balances, /groups/a%2Fb/balances). Record statuses.
  - Outcomes that would be acceptable: 400 for empty, missing or non-string ids is fine. Rejecting awkward or overlong ids with 400, or accepting them, are both fine, as long as every id that got 201 is reachable by balances, settlements and expenses.
- **U-5**: Whether exact shares may be negative or non-integer (for example {"Ann": 150, "Bob": -50} or {"Ann": 50.5, "Bob": 49.5} for cents 100), since only zero is said to be allowed and only the total is said to be checked.
  - Probe: Create group g with ["Ann","Bob"]. POST /groups/g/expenses {"payer": "Ann", "cents": 100, "split": "exact", "shares": {"Ann": 150, "Bob": -50}}, then {"payer": "Ann", "cents": 100, "split": "exact", "shares": {"Ann": 50.5, "Bob": 49.5}}. Record both statuses and GET /groups/g/balances.
  - Outcomes that would be acceptable: 400 for fractional shares is the fitting reading of 'whole cents'. 400 for negative shares is the expected reading; accepting integer negative shares is a judgement call only if documented. Balances stay whole cents summing to 0.
- **U-6**: How a member list is handled when it holds two distinct non-empty names plus a duplicate, an empty or whitespace-only entry (for example ["Ann", "Ann", "Bob"] or ["Ann", " ", "Bob"]), and whether names differing only in case or surrounding spaces count as distinct.
  - Probe: POST /groups {"id": "d", "members": ["Ann", "Ann", "Bob"]}; if 201, POST /groups/d/expenses {"payer": "Ann", "cents": 100, "split": "equal"} and GET /groups/d/balances. POST /groups {"id": "w", "members": ["Ann", " ", "Bob"]}, {"id": "s", "members": [" ", "Bob"]} and {"id": "c", "members": ["Ann", "ann"]}. Record statuses and any balances.
  - Outcomes that would be acceptable: Rejecting a list with a repeated name with 400, or accepting it and de-duplicating while keeping first-listed order, are both fine; a member must never be counted twice. Case variants being distinct is fine; whitespace-only names rejected or accepted are both defensible if consistent.
- **U-8**: Whether an expense or group is already safely written to DATA_FILE when its 201 is sent, and whether a crash or kill during a write can leave DATA_FILE truncated or corrupt.
  - Probe: Start with DATA_FILE set to a new path, create group g, POST an expense and send SIGKILL to the server as soon as the 201 arrives. Restart with the same DATA_FILE and GET /groups/g/balances; check the file parses as JSON. Repeat while sending many POSTs in a loop and killing mid-stream; check the file still parses and every expense that got 201 is reflected.
  - Outcomes that would be acceptable: Every acknowledged write is present after restart and the file always parses (for example a write to a temporary file then rename before replying). A synchronous write before replying without atomic rename is weaker but acceptable at this scale.
- **U-9**: What the server does when DATA_FILE names a file that does not exist yet.
  - Probe: Run server.js with PORT set and DATA_FILE set to an absent file in an existing directory. Check whether it starts, whether the file appears at startup or on the first write, then POST a valid group, stop, read the file, restart and GET the group's balances.
  - Outcomes that would be acceptable: Starting with an empty store, creating the file at startup or on the first successful write, and finding the group after restart. Failing at start is not acceptable for an absent file in a writable directory.
- **U-10**: What the server does at startup when DATA_FILE is empty or holds invalid JSON.
  - Probe: Write `{broken` into the DATA_FILE and start the server; record whether it refuses to start, starts empty, or starts and later overwrites the file. Repeat with an empty file; if it starts, create a group and check whether the original file content was preserved.
  - Outcomes that would be acceptable: Refusing to start with a clear error, or starting while preserving the bad file (for example renamed aside), are fine. Silently overwriting it is not.
- **U-13**: Whether concurrent expense posts to one group each get a distinct expense number with no repeats or gaps, and each acknowledged expense is applied exactly once.
  - Probe: Create group g with ["Ann","Bob"]. Fire 100 POST /groups/g/expenses {"payer": "Ann", "cents": 2, "split": "equal"} at once. Collect every status and expense number, then GET /groups/g/balances.
  - Outcomes that would be acceptable: The numbers on the 201s are exactly 1..N, each once, in any order across responses; Ann's net is N and Bob's -N. Some requests failing is fine if each 201 is reflected once and failures leave nothing stored.
- **U-15**: What two overlapping POST /groups calls for the same new id do.
  - Probe: With an empty DATA_FILE, send 20 concurrent POST /groups {"id": "race", "members": ["Ann","Bob"]} (or two with different member lists). Count 201s and 409s, GET /groups/race/balances, restart with the same DATA_FILE and GET again.
  - Outcomes that would be acceptable: Exactly one 201 and the rest 409, one stored group whose members are those of the 201 request, the same after restart.
- **U-16**: Whether expense numbering continues after a restart instead of starting again at 1.
  - Probe: Create group g, POST three expenses, restart with the same DATA_FILE, POST one more expense and record the number.
  - Outcomes that would be acceptable: The next expense is numbered 4.
- **U-21**: Which status POST /groups uses when the id already exists and the member list is also invalid, and whether the stored members change.
  - Probe: POST /groups {"id": "g", "members": ["Ann","Bob"]}. POST /groups {"id": "g", "members": ["Ann"]}. Record the status, then GET /groups/g/balances and check which names are keys.
  - Outcomes that would be acceptable: 400 or 409 are both fine; the stored members stay Ann and Bob.
- **U-25**: Whether GET /groups/<id>/balances and GET /groups/<id>/settlements only read, or also change stored state.
  - Probe: Create group g with ["Ann","Bob"], POST an equal expense paid by Ann for 100. GET balances, GET settlements, GET balances, GET settlements, and compare the bodies.
  - Outcomes that would be acceptable: Both balances bodies match and both settlements bodies match; the GETs write nothing.
- **U-26**: Whether DATA_FILE written by the server is read back to the same state: a group with both an equal and an exact expense gives the same balances, settlements and next expense number after restart.
  - Probe: Point DATA_FILE at a new path. Create a group, record one equal and one exact expense, and copy the balances and settlements bodies. Read DATA_FILE while the server is up. Restart with the same file, GET balances and settlements, compare, and POST one more expense.
  - Outcomes that would be acceptable: Any JSON layout the server writes and reads back with identical balances and settlements and the next number 3 is fine; balances may be stored or computed on read. A hand-written file of another shape does not have to load.
- **U-27**: Whether the tests are self-contained: they start their own server on a free port with a temporary DATA_FILE, need nothing running, leave no stray files or processes, and pass repeatedly.
  - Probe: On a clean checkout with nothing listening, run `node --test` from the project root twice in a row, and once while another process holds a common port such as 3000. Check the exit code is 0 each time, no new files remain in the project folder, and no node process is left running.
  - Outcomes that would be acceptable: Any self-contained approach (spawning server.js on port 0 or a free port, or importing the server) is fine.
- **U-31**: Whether a group creation and an expense in another group, sent at the same time, both survive a restart.
  - Probe: With an existing group g, send at the same time POST /groups {"id": "h", "members": ["Cy","Di"]} and POST /groups/g/expenses with a valid expense. After both return 201, restart with the same DATA_FILE and GET /groups/g/balances and /groups/h/balances. Repeat many times.
  - Outcomes that would be acceptable: Every time, g's balances include the expense and h exists with members Cy and Di.
- **U-35**: What happens when a client disconnects in the middle of sending a request body.
  - Probe: Create group g. Open a connection, send POST /groups/g/expenses headers with Content-Length 1000 and only part of a body, then close the socket. Repeat several times, then GET /groups/g/balances and POST a valid expense.
  - Outcomes that would be acceptable: No expense is stored from the aborted requests, the server stays up, and the following requests work.

## The defect table (each defect with what each delivery did when it was tried)

- **D-1** (low) A DATA_FILE holding valid JSON without a "groups" array is silently treated as empty and overwritten. Expected: Refuse to start with a clear error (as it does for invalid JSON) or keep the original file aside before writing. — X: absent; Y: absent; Z: present
- **D-2** (low) A kill during a write leaves stray .expenses-<uuid>.tmp files beside DATA_FILE that startup never removes. Expected: No stale temporary files accumulating beside the data file (or removal at startup). — X: present; Y: present; Z: present

## Audit of delivery X

```json
{
 "code": "X",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "Ran PORT=47258 DATA_FILE=work/.../s1.json node server.js; it printed 'Listening on port 47258' and served every probe below.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Inserted process.exit(1); after 'use strict' in server.js: all 13 tests failed (e.g. 'creates groups on the configured port and preserves the original on duplicates'). Restored; suite back to 13/13 pass."
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "server.js requires only node:crypto, node:fs/promises, node:http, node:path, node:util; no package.json or node_modules; it started and served requests from the bare copy.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47258 -> 'Listening on port 47258' and HTTP requests to 127.0.0.1:47258 answered.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "After creating groups/expenses, cat DATA_FILE showed {\"groups\":[{\"id\":\"g\",\"members\":[\"Ann\",\"Bob\",\"Cy\"],\"expenses\":[{\"payer\":\"Ann\",\"cents\":100,\"shares\":[34,33,33]},...]}]}; new file created at the named path on first write.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed resolve(DATA_FILE) to resolve('ledger-fixed.json'): 9 of 13 tests failed (e.g. 'a failed ledger replacement preserves the saved expense and next number', 'commits overlapping mutations once each and resumes the ledger after restart'). Restored; 13/13 pass."
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "Stopped (SIGTERM) and restarted with same DATA_FILE: GET /groups/g/balances -> 200 {\"Ann\":13,\"Bob\":15,\"Cy\":-28}; POST /groups {id:g} -> 409.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "After restart, balances and settlements identical to before; next expense numbered 4.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\",\"Bob\",\"Cy\"]} -> 201 (empty body).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "Second POST /groups {id:g,...} -> 409; also 409 after restart.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\"] -> 400; [] -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\",\"Ann\"] -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Removed '&& new Set(members).size === members.length' from validMembers: 'creates groups on the configured port and preserves the original on duplicates' failed. Restored; 13/13 pass."
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\",\"\"] -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups/g/expenses {payer:Ann,cents:100,split:equal} -> 201 {\"expense\":1}; balances credit Ann +100 paid; payer Zed -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "Group [Ann,Bob,Cy], Ann pays 100 equal -> balances {\"Ann\":66,\"Bob\":-33,\"Cy\":-33}; file shares [34,33,33]. 60 random groups matched a reference implementation.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "Group [Zed,Amy,Bo], Bo pays 11 equal -> {\"Zed\":-4,\"Amy\":-4,\"Bo\":8} (Zed, Amy listed first get the extra cents); [X,Y,Z] 2 cents -> X -1, Y -1, Z +2.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "Bob pays 50 exact {Ann:50,Cy:0} -> 201 {\"expense\":2}; Ann debited 50, Cy 0.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "shares {Ann:50, Cy:0} accepted (201); {Ana:0,...} style zero accepted.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "Bob pays 50 exact {Ann:40,Cy:0} -> 400; {Ann:60} -> 400; {} -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Deleted 'if (totalShares(amounts) !== BigInt(cents)) return null;' in expenseFrom: 'rejects invalid submissions without changing data or consuming a number' failed. Restored; 13/13 pass."
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "Valid expense -> 201 body {\"expense\":1}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "Expenses in g numbered 1,2,3 (rejected ones did not consume numbers); other groups start at 1.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "payer Zed -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "exact shares {Zed:50} -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "cents 0 -> 400; cents -5 -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed the check in expenseFrom to 'if (!isWholeCent(cents, numbers.cents)) return null;' (dropped '|| cents <= 0'): 'rejects invalid submissions without changing data or consuming a number' failed. Restored; 13/13 pass."
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "cents 1.5 -> 400; 1.000000000000000001 -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "split 'weird' -> 400; split 'percent' with shares {Ann:10}, cents 10 -> 400.",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "Removed \"|| (split !== 'equal' && split !== 'exact')\" from expenseFrom: the probe {payer:Ann,cents:10,split:'percent',shares:{Ann:10}} then got 201, but all 13 tests still passed (the test's unknown-split bodies have no shares and are rejected by the exact path anyway). Restored; 13/13 pass."
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "shares totalling 40 or 60 for cents 50 -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/balances -> 200 {\"Ann\":16,\"Bob\":17,\"Cy\":-33} (every member a key, zero members included).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "Ann paid 100 owed 34 -> 66; Bob paid 50 owed 33 -> 17 after second expense; random 60-group comparison with reference: 0 mismatches.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "All observed balance objects summed to 0, including the 60 random groups.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/settlements -> 200 [{\"from\":\"Cy\",\"to\":\"Bob\",\"cents\":17},{\"from\":\"Cy\",\"to\":\"Ann\",\"cents\":16}]; no expenses -> [].",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "Replaying every returned settlement list (60 random groups and fixed cases) brings all balances to 0.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "Group [A,B,C,D] balances {A:100,B:-70,C:-70,D:40} -> [B->A 70, C->D 40, C->A 30]; random groups matched the greedy reference exactly.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "Group [Bob,Ann,Cy,Dee] balances {Bob:-100,Ann:-100,Cy:100,Dee:100} -> [Bob->Cy 100, Ann->Dee 100] (first-listed debtor and creditor).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/nope/balances 404, /settlements 404, POST /groups/nope/expenses 404 (also with body {}); PUT /groups/nope/balances 404.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "100 concurrent equal expenses of 2 cents: 100 x 201, numbers exactly 1..100, balances {Ann:100,Bob:-100}, same after restart.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "node --test from the copy's root: 13 tests in test/service.test.js, 13 pass, exit 0.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "400 with empty body for '{' and 'not json' on POST /groups and on POST /groups/g/expenses; server keeps serving, nothing stored.",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups raw '{' -> 400; raw 'not json' -> 400; POST /groups/g/expenses raw 'not json' -> 400; then POST /groups g9 -> 201, GET /groups/g/balances -> 200 {Ann:0,Bob:0}.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400. ... Error responses have empty bodies.\""
  },
  {
   "id": "U-2",
   "behaviour": "400 for every missing-field case; nothing stored.",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups/g/expenses {} / {payer,cents} / {cents,split} / {payer,split} / exact without shares -> 400 each; POST /groups {} -> 400, {id:h} -> 400; balances g {Ann:0,Bob:0}; /groups/h/balances 404.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400.\""
  },
  {
   "id": "U-3",
   "behaviour": "Wrong types refused with 400, no coercion.",
   "handling": "sound",
   "observed": true,
   "evidence": "members 'Ann,Bob' -> 400; ['Ann',7,'Bob'] -> 400; cents '100' -> 400; shares [100] -> 400; cents true / null -> 400; share '10' -> 400; g2 balances unchanged {Ann:0,Bob:0}.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "'' , missing and numeric ids -> 400; '.' -> 400 (reserved); 'a/b', 'a b', '50%', 'café' -> 201 and reachable by balances, settlements and expenses through encodeURIComponent paths; new ids capped at 16 KiB encoded.",
   "handling": "sound",
   "observed": true,
   "evidence": "a%2Fb, a%20b, 50%25, caf%C3%A9: balances 200, settlements 200 [], expense 201 {expense:1}; malformed escape /groups/%E0%A4%A/balances -> 404.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A group ID is a nonempty, URL-encodable string. The IDs `.` and `..` are reserved. Send the original ID in the creation body, then use `encodeURIComponent(id)` once to address it as a single path segment. New IDs may occupy up to 16 KiB (16,384 bytes) after encoding.\""
  },
  {
   "id": "U-5",
   "behaviour": "Negative and fractional exact shares rejected with 400; balances stay whole and zero-sum.",
   "handling": "sound",
   "observed": true,
   "evidence": "shares {Ann:150,Bob:-50} -> 400; {Ann:50.5,Bob:49.5} -> 400; GET /groups/g/balances {Ann:0,Bob:0}.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Every listed member must belong to the group, and the nonnegative whole-cent shares must sum to the expense amount.\""
  },
  {
   "id": "U-6",
   "behaviour": "Any repeated name -> 400; whitespace-only names accepted as ordinary distinct names; case variants distinct; no trimming.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "['Ann','Ann','Bob'] -> 400; ['Ann',' ','Bob'] -> 201 and a 99-cent equal expense gives {Ann:66,' ':-33,Bob:-33}; [' ','Bob'] -> 201; ['Ann','ann'] -> 201.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Supply at least two members, each with a distinct, nonempty string name. Names match exactly, including whitespace.\""
  },
  {
   "id": "U-8",
   "behaviour": "Writes a temp file in DATA_FILE's directory then renames over DATA_FILE before replying (no fsync). Every acknowledged expense survives SIGKILL; the file always parses. Killed writes leave orphan .expenses-<uuid>.tmp files.",
   "handling": "sound",
   "observed": true,
   "evidence": "SIGKILL right after a 201: restart shows {Ann:5,Bob:-5}, file parses. 10 rounds of 8 parallel POST loops killed mid-stream: file parsed every time, stored count >= acknowledged count every time (one round stored 359 for 358 acks); 9 orphan .tmp files left in the data directory.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"The service replaces the JSON snapshot atomically and acknowledges each mutation after the replacement.\""
  },
  {
   "id": "U-9",
   "behaviour": "Starts with an empty store; file appears on the first successful write; group found after restart. A missing parent directory makes startup fail.",
   "handling": "sound",
   "observed": true,
   "evidence": "Absent file: started, file absent at start, POST /groups -> 201 and file created {\"groups\":[{\"id\":\"g\",...}]}; restart -> balances 200. DATA_FILE in a missing directory -> exit 1 'ENOENT ... stat .../nodir'.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"An existing, writable parent directory is sufficient for a new ledger. The first successful write creates the file.\""
  },
  {
   "id": "U-10",
   "behaviour": "Refuses to start (exit 1) for '{broken' and for an empty file, printing the JSON SyntaxError stack (without naming the file); the file content is left untouched.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "'{broken': exit 1 'SyntaxError: Expected property name or '}' in JSON at position 1', content still '{broken'. Empty file: exit 1 'SyntaxError: Unexpected end of JSON input', content still ''.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid port configuration, an unavailable port, and unreadable or incompatible saved data cause startup to fail.\""
  },
  {
   "id": "U-13",
   "behaviour": "Single write queue: 100 concurrent posts all got 201 with numbers exactly 1..100, each applied once.",
   "handling": "sound",
   "observed": true,
   "evidence": "100 x 201, sorted numbers == 1..100, balances {Ann:100,Bob:-100}, same after restart.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Overlapping expenses receive numbers in the order their validated requests enter the write queue.\""
  },
  {
   "id": "U-15",
   "behaviour": "Exactly one 201 and 19 x 409; stored members are the 201 request's; same after restart.",
   "handling": "sound",
   "observed": true,
   "evidence": "20 concurrent POST /groups id race (first ['Ann','Bob'], others with a third member): {201:1, 409:19}, winner was request 0, balances {Ann:0,Bob:0} before and after restart.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Group creations and expense submissions share a write queue across all groups.\" and \"Creating a group with a valid list and a used ID returns 409.\""
  },
  {
   "id": "U-16",
   "behaviour": "Numbering continues after restart.",
   "handling": "sound",
   "observed": true,
   "evidence": "3 expenses, restart, next expense -> 201 {\"expense\":4}.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"The number increments with each saved expense in that group.\" with \"To keep your groups and expenses across restarts, use the same path.\""
  },
  {
   "id": "U-21",
   "behaviour": "400 (member validation comes before the existence check); stored members stay Ann and Bob.",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups {id:g,members:['Ann']} with g existing -> 400; GET /groups/g/balances -> {Ann:0,Bob:0}.",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400. Creating a group with a valid list and a used ID returns 409.\""
  },
  {
   "id": "U-25",
   "behaviour": "Read-only: repeated GETs return identical bodies and do not touch the file.",
   "handling": "sound",
   "observed": true,
   "evidence": "balances {Ann:50,Bob:-50} twice, settlements [{from:Bob,to:Ann,cents:50}] twice; DATA_FILE mtime unchanged.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Reading the list leaves the ledger unchanged.\""
  },
  {
   "id": "U-26",
   "behaviour": "Writes {groups:[{id,members,expenses:[{payer,cents,shares:[per member]}]}]}; reads it back to identical balances, settlements and numbering.",
   "handling": "sound",
   "observed": true,
   "evidence": "Equal + exact expense: balances {Ann:66,Bob:-3,Cy:-63}, settlements [Cy->Ann 63, Bob->Ann 3] identical after restart; next expense 3.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"To keep your groups and expenses across restarts, use the same path.\""
  },
  {
   "id": "U-27",
   "behaviour": "Tests spawn server.js on port 0 (or an OS-chosen free port) with a mkdtemp DATA_FILE removed after each test; pass repeatedly and with port 3000 held; no new files in the project, no node processes left.",
   "handling": "sound",
   "observed": true,
   "evidence": "node --test twice: exit 0 both; again with a listener on :3000: exit 0; find before/after identical; no X server.js processes remained.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-31",
   "behaviour": "Both mutations go through one queue over the whole snapshot; both survive restart every time.",
   "handling": "sound",
   "observed": true,
   "evidence": "25 rounds of concurrent POST /groups h<i> {Cy,Di} + expense in g: all 201; after restart g {Ann:25,Bob:-25}, all 25 h groups {Cy:0,Di:0}.",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Group creations and expense submissions share a write queue across all groups.\""
  },
  {
   "id": "U-35",
   "behaviour": "Aborted uploads are discarded; nothing stored; server stays up.",
   "handling": "sound",
   "observed": true,
   "evidence": "5 connections sent Content-Length 1000 with a 43-byte body then closed: balances {Ann:0,Bob:0}; next valid expense 201; balances {Ann:50,Bob:-50}.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Exact decimal validation of number spellings (10e-1 and 1.0 accepted as 1; 1.00000000000000001 and 1e-500 rejected) using JSON.parse source context with a regex fallback",
   "where": "server.js readNumberSources, isWholeCent",
   "worth": "neutral",
   "why": "prevents silent rounding of non-whole inputs, but adds subtle parsing code for an edge the request does not raise"
  },
  {
   "what": "Safe-integer guard on amounts and on resulting balances (overflowing expense rejected with 400)",
   "where": "server.js balancesFit, maxCents",
   "worth": "value",
   "why": "keeps balances exact instead of losing precision"
  },
  {
   "what": "16 KiB limit on new group ids and header-size budget grown from the longest saved id",
   "where": "server.js maxNewIdLength, createService maxHeaderSize",
   "worth": "value",
   "why": "guarantees every group that got 201 stays addressable (no 431)"
  },
  {
   "what": "Startup validation of the saved ledger (structure, members, shares summing, balance range)",
   "where": "server.js loadGroups, validSavedExpense",
   "worth": "value",
   "why": "refuses to run on corrupt or inconsistent data instead of overwriting it"
  },
  {
   "what": "README section on recording a completed settlement payment as an exact expense",
   "where": "README.md 'Record a settlement payment'",
   "worth": "neutral",
   "why": "documentation of existing endpoint use; no new behaviour"
  },
  {
   "what": "Reserved ids '.' and '..'",
   "where": "server.js encodedGroupIdLength",
   "worth": "neutral",
   "why": "avoids path-normalisation confusion; harmless restriction"
  },
  {
   "what": "Builders' acceptance harness scripts shipped in the product folder",
   "where": "acceptance/*.cjs",
   "worth": "neutral",
   "why": "not run by node --test and not used by the service; extra material for a maintainer to understand or ignore"
  }
 ],
 "spec_notes": "The spec leaves many points 'Open:' for the requester (C-2 PORT handling, C-4 malformed saved data and write failures, C-5 id rules, C-6 409-vs-400 precedence, C-8 duplicates/whitespace, C-14 large amounts, C-23 malformed-body statuses, C-40 crash recovery) while the product and README settle all of them (e.g. 400 before 409, 16 KiB ids, safe-integer cap, startup failure on bad data); the spec was not updated to say these were decided. C-21 rejects negative exact shares and C-14/C-8 reject string cents and non-list members with 'Source: request', though the request only says zero is allowed and only checks the total: decisions made without marking. Clauses pin choices a correct product need not share: C-43/C-48 (behaviour after a failed ledger write), C-46 (equivalent number spellings such as 10e-1 accepted), C-47/C-49 (long-id limits and upgrade of saved long ids), C-45 (prototype-named members). The file has two '## Use cases' and two '## Clauses' headings because later cycles were appended. No clause contradicts the request.",
 "tests_notes": "13 integration tests in one file, each spawning server.js on port 0 with a mkdtemp ledger. Several cover many behaviours at once: 'rejects invalid submissions...' asserts about 15 different 400s plus three 404s and the numbering; 'creates groups on the configured port...' covers PORT, every member-list rejection, 409, preservation and the creation race; 'commits overlapping mutations...' covers concurrency, persistence and numbering after restart. Tied to internals: the two failed-write tests preload a script that monkeypatches fs/promises rename with DATA_FILE as target, so a build that writes with writeFileSync or renames differently would not trigger the failure (and creation is asserted to return exactly 500); 'reopens and appends...' and 'long IDs already saved...' hand-write the ledger in this product's own {groups:[{id,members,expenses:[{payer,cents,shares:[...]}]}]} layout; start() waits for the exact log line 'Listening on port N'. Would fail on another correct build: the 16 KiB id limit and 400 above it, 400 for 1.00000000000000001 and 1e-500, acceptance of 10e-1/2.00E+0, the fixed-layout ledger files and the log-line format. Unknown split is only tested without shares, so dropping the split check goes unnoticed (S-24 break passed).",
 "maintainer": "The whole-cent check re-parses the raw body (JSON.parse source context, or a regex fallback for older Node) and must stay in step with the parsed values; changing how bodies are read is easy to get subtly wrong. Expenses are stored as positional share arrays aligned to the members order, so any change to membership or the file layout needs a migration that loadGroups' strict validation will otherwise refuse. The single global commit queue with copy-on-write Maps, and maxHeaderSize derived from the longest saved id, are coupled invariants that are not obvious from the routes."
}
```

## Audit of delivery Y

```json
{
 "code": "Y",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "node server.js started from the copy with PORT and DATA_FILE and printed \"Listening on port 47321\"; every probe below ran against it",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: prefixed the final main().catch(...) call with `false &&` so server.js never listens; all 6 tests failed; restored, 6/6 pass"
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "server.js requires only node:crypto, node:fs/promises, node:http, node:path, node:util; no package.json or node_modules in the product; it started and served with nothing installed",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47321 DATA_FILE=<work>/probe-data/stated.json node server.js; requests to 127.0.0.1:47321 answered (POST /groups -> 201)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "after creating groups and expenses, DATA_FILE probe-data/stated.json held {\"groups\":[{\"id\":\"g\",\"members\":[\"Ann\",\"Bob\",\"Cy\"],\"expenses\":[{\"payer\":\"Ann\",\"cents\":100,\"shares\":[34,33,33]},...]}]} and parsed as JSON",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: `resolve(DATA_FILE)` -> `resolve(DATA_FILE + '.other')`; failed: 'commits overlapping mutations once each and resumes the ledger after restart' (readFile of DATA_FILE ENOENT); restored, 6/6 pass"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "SIGTERM the server, restart with the same DATA_FILE: GET /groups/t/settlements -> 200 [{\"from\":\"A\",\"to\":\"C\",\"cents\":10},{\"from\":\"B\",\"to\":\"D\",\"cents\":10}] (group t and its expenses present)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "after restart GET /groups/g/balances -> 200 {\"Ann\":33,\"Bob\":15,\"Cy\":-48}, identical to before the stop",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\",\"Bob\",\"Cy\"]} -> 201 (empty body)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\",\"Bob\"]} again -> 409",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups members [\"Ann\"] -> 400; members [] -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"h2\",\"members\":[\"Ann\",\"Ann\"]} -> 400",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: in validMembers replaced `new Set(members).size === members.length` with `true`; failed: 'creates groups on the configured port and preserves the original on duplicates'; restored, 6/6 pass"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"h3\",\"members\":[\"Ann\",\"\"]} -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups/g/expenses {\"payer\":\"Ann\",\"cents\":100,\"split\":\"equal\"} -> 201 {\"expense\":1}; payer credited (Ann +66)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "group [Ann,Bob,Cy], 100 equal paid by Ann -> balances {\"Ann\":66,\"Bob\":-33,\"Cy\":-33}; stored shares [34,33,33]",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "100 among 3 -> shares [34,33,33] (first member gets the extra cent); 1 cent paid by Cy among Ann,Bob,Cy -> {\"Ann\":-1,\"Bob\":0,\"Cy\":1}; 101 among 3 -> shares [34,34,33]",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "exact 50 paid by Bob shares {\"Ann\":30,\"Cy\":20,\"Bob\":0} -> 201 {\"expense\":2}; balances went from {66,-33,-33} to {\"Ann\":36,\"Bob\":17,\"Cy\":-53}",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "same expense with \"Bob\":0 accepted -> 201",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "exact 50 shares {\"Ann\":30,\"Cy\":10} -> 400; shares {\"Ann\":30,\"Cy\":30} -> 400",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: deleted `if (totalShares(amounts) !== BigInt(cents)) return null;` in expenseFrom; failed: 'rejects invalid submissions without changing data or consuming a number'; restored, 6/6 pass"
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "valid expense -> 201 with body {\"expense\":1}, Content-Type application/json",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "successive expenses in g returned {\"expense\":1}, {\"expense\":2}, {\"expense\":3}; rejected ones took no number; a new group starts at 1",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "payer \"Zed\" -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "exact shares {\"Ann\":25,\"Zed\":25} -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "cents 0 -> 400; cents -5 -> 400",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: `if (!isWholeCent(cents, numbers.cents) || cents <= 0) return null;` -> dropped `|| cents <= 0`; failed: 'rejects invalid submissions without changing data or consuming a number'; restored, 6/6 pass"
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "cents 10.5 -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "split \"percent\" -> 400",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "edit: split guard `(split !== 'equal' && split !== 'exact')` -> `typeof split !== 'string'` and `if (split === 'equal')` -> `if (split !== 'exact')` (unknown split treated as equal); failed: 'rejects invalid submissions without changing data or consuming a number'; restored, 6/6 pass"
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "shares summing to 40 or 60 for cents 50 -> 400; exact with shares {} -> 400",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/balances -> 200 {\"Ann\":33,\"Bob\":15,\"Cy\":-48}, one key per member, members with no activity shown as 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "after 100 equal by Ann, 50 exact by Bob (Ann30,Cy20), 7 equal by Cy: Ann 100-34-30-3=33, Bob 50-33-0-2=15, Cy 7-33-20-2=-48, matching the response",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "sum of {\"Ann\":33,\"Bob\":15,\"Cy\":-48} = 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/settlements -> 200 [{\"from\":\"Cy\",\"to\":\"Ann\",\"cents\":33},{\"from\":\"Cy\",\"to\":\"Bob\",\"cents\":15}]",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "applying those payments to the balances gave {\"Ann\":0,\"Bob\":0,\"Cy\":0}",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "Cy (owes most, 48) pays Ann (owed most, 33) 33, then Bob 15; 4-member group spec example reproduced by the suite ordering",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "balances {\"A\":-10,\"B\":-10,\"C\":10,\"D\":10} -> [{\"from\":\"A\",\"to\":\"C\",\"cents\":10},{\"from\":\"B\",\"to\":\"D\",\"cents\":10}]; creditor tie A:-20,B:10,C:10 -> A pays B first, then C",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/nope/balances -> 404; GET /groups/nope/settlements -> 404; POST /groups/nope/expenses valid body -> 404, garbage body -> 404",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "100 concurrent POST /groups/g/expenses {\"payer\":\"Ann\",\"cents\":2,\"split\":\"equal\"}: 100x 201, numbers exactly 1..100, balances {\"Ann\":100,\"Bob\":-100}, same after restart; 25 rounds of concurrent group-create + expense all present after restart",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "`node --test` in the project root ran test/service.test.js (node:test): 6 tests, 6 pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "400 with empty body for each malformed body; server keeps serving and stores nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups body `{` -> 400; body `not json` -> 400; POST /groups/g/expenses body `not json` -> 400; then POST /groups g9 -> 201 and GET /groups/g/balances -> 200 {\"Ann\":0,\"Bob\":0}",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400. ... Error responses have empty bodies.\""
  },
  {
   "id": "U-2",
   "behaviour": "400 for every missing field; nothing stored",
   "handling": "sound",
   "observed": true,
   "evidence": "expenses {} / no split / no payer / no cents / exact without shares -> 400 each; POST /groups {} -> 400, {\"id\":\"h\"} -> 400; GET /groups/g/balances -> {\"Ann\":0,\"Bob\":0}; GET /groups/h/balances -> 404",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400.\""
  },
  {
   "id": "U-3",
   "behaviour": "wrong types refused with 400, no coercion",
   "handling": "sound",
   "observed": true,
   "evidence": "members \"Ann,Bob\" -> 400; members [\"Ann\",7,\"Bob\"] -> 400; cents \"100\" -> 400; shares [100] -> 400; g2 balances stayed {\"Ann\":0,\"Bob\":0}",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "empty, missing and numeric ids -> 400; \"a/b\", \"a b\", \"50%\", \"café\" -> 201 and each reachable percent-encoded by expenses, balances and settlements; \".\" and \"..\" reserved",
   "handling": "sound",
   "observed": true,
   "evidence": "id \"\" -> 400, none -> 400, 1 -> 400; a/b, \"a b\", 50%, café: create 201, POST /groups/<encodeURIComponent(id)>/expenses 201, balances 200 {\"Ann\":5,\"Bob\":-5}, settlements 200",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"A group ID is a nonempty, URL-encodable string. The IDs `.` and `..` are reserved. Encode the ID as a single path segment, for example with `encodeURIComponent(id)`.\""
  },
  {
   "id": "U-5",
   "behaviour": "negative and fractional shares both rejected with 400",
   "handling": "sound",
   "observed": true,
   "evidence": "shares {\"Ann\":150,\"Bob\":-50} -> 400; {\"Ann\":50.5,\"Bob\":49.5} -> 400; balances {\"Ann\":0,\"Bob\":0}",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Every listed member must belong to the group, and the nonnegative whole-cent shares must sum to the expense amount.\""
  },
  {
   "id": "U-6",
   "behaviour": "any repeated name rejected (400); whitespace-only names accepted as ordinary distinct names; case variants distinct",
   "handling": "sound",
   "observed": true,
   "evidence": "[\"Ann\",\"Ann\",\"Bob\"] -> 400; [\"Ann\",\" \",\"Bob\"] -> 201, balances {\"Ann\":0,\" \":0,\"Bob\":0}; [\" \",\"Bob\"] -> 201; [\"Ann\",\"ann\"] -> 201, balances {\"Ann\":0,\"ann\":0}",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Supply at least two members, each with a distinct, nonempty string name. Names match exactly, including whitespace, and the member array sets the order used for splits and settlements.\""
  },
  {
   "id": "U-8",
   "behaviour": "snapshot written to a temp file and renamed over DATA_FILE before the 201; every acknowledged write survived SIGKILL and the file always parsed; killed writes leave orphan .expenses-<uuid>.tmp files beside DATA_FILE",
   "handling": "sound",
   "observed": true,
   "evidence": "SIGKILL right after a 201: restart shows {\"Ann\":5,\"Bob\":-5}, file parses; 8 rounds of 10 parallel POST loops killed mid-stream (680-772 acks per round): every round file parsed and balance delta equalled the acked count exactly; 3 leftover .tmp files after the rounds",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"The service serializes mutations across all groups, replaces the JSON snapshot atomically, and acknowledges each mutation after the replacement.\""
  },
  {
   "id": "U-9",
   "behaviour": "starts with an empty store; file created on the first successful write; group found after restart. A missing parent directory makes startup fail with ENOENT",
   "handling": "sound",
   "observed": true,
   "evidence": "absent file: started, file absent at start; POST /groups -> 201, file now exists; restart -> GET /groups/a/balances 200 {\"Ann\":0,\"Bob\":0}",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"An existing, writable parent directory is sufficient for a new ledger. The first successful write creates the file.\""
  },
  {
   "id": "U-10",
   "behaviour": "refuses to start (exit 1) and leaves the file untouched; the error is a raw JSON SyntaxError stack that does not name the data file",
   "handling": "acceptable",
   "observed": true,
   "evidence": "DATA_FILE \"{broken\": exit 1, stderr \"SyntaxError: Expected property name or '}' in JSON at position 1\", file still \"{broken\"; empty file: exit 1 \"SyntaxError: Unexpected end of JSON input\", file still empty",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid port configuration, an unavailable port, and unreadable or incompatible saved data cause startup to fail.\""
  },
  {
   "id": "U-13",
   "behaviour": "distinct numbers 1..N, each expense applied once",
   "handling": "sound",
   "observed": true,
   "evidence": "100 concurrent posts: 100x 201, sorted numbers exactly 1..100, balances {\"Ann\":100,\"Bob\":-100}",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Overlapping expenses receive numbers in the order their validated requests enter the write queue.\""
  },
  {
   "id": "U-15",
   "behaviour": "exactly one 201, rest 409; stored members are those of the winning request; same after restart",
   "handling": "sound",
   "observed": true,
   "evidence": "20 concurrent POST /groups id race (request 0 with [Ann,Bob], others [Cy,Di]): one 201 (request 0), 19x 409; balances {\"Ann\":0,\"Bob\":0}, same after restart",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"The service serializes mutations across all groups ...\" and \"Creating a group with a valid list and a used ID returns 409.\""
  },
  {
   "id": "U-16",
   "behaviour": "numbering continues after restart",
   "handling": "sound",
   "observed": true,
   "evidence": "three expenses in g, restart, next POST -> {\"expense\":4}",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"The number increments with each saved expense in that group.\" with \"To keep your groups and expenses across restarts, use the same path.\""
  },
  {
   "id": "U-21",
   "behaviour": "validation runs first: 400; stored members unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\"]} after g existed -> 400; GET /groups/g/balances keys Ann, Bob",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"Invalid submissions return 400. Creating a group with a valid list and a used ID returns 409.\""
  },
  {
   "id": "U-25",
   "behaviour": "GETs are pure reads",
   "handling": "sound",
   "observed": true,
   "evidence": "balances, settlements, balances, settlements bodies identical ({\"Ann\":50,\"Bob\":-50} and [{\"from\":\"Bob\",\"to\":\"Ann\",\"cents\":50}]); DATA_FILE mtime unchanged",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "README.md: \"Reading the list leaves the ledger unchanged.\""
  },
  {
   "id": "U-26",
   "behaviour": "round-trips exactly: per-expense shares arrays stored; same balances, settlements and next number",
   "handling": "sound",
   "observed": true,
   "evidence": "equal 101 + exact 40: balances {\"Ann\":57,\"Bob\":6,\"Cy\":-63} and settlements identical after restart; next expense -> {\"expense\":3}",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"To keep your groups and expenses across restarts, use the same path.\""
  },
  {
   "id": "U-27",
   "behaviour": "tests spawn server.js on port 0 or a free port with a mkdtemp DATA_FILE and clean up",
   "handling": "sound",
   "observed": true,
   "evidence": "`node --test` twice: exit 0, 6/6 each; once more while another process already held port 3000: exit 0; find before/after showed no new files in the project; no server process left",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-31",
   "behaviour": "both survive every time",
   "handling": "sound",
   "observed": true,
   "evidence": "25 rounds of simultaneous POST /groups h<i> [Cy,Di] and POST /groups/g/expenses: all 201; after restart all 25 groups {\"Cy\":0,\"Di\":0} and g balances include all 25 expenses",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"The service serializes mutations across all groups, replaces the JSON snapshot atomically, and acknowledges each mutation after the replacement.\""
  },
  {
   "id": "U-35",
   "behaviour": "aborted uploads store nothing; server keeps serving",
   "handling": "sound",
   "observed": true,
   "evidence": "5 sockets sent headers with Content-Length 1000 and a partial body then closed; GET /groups/p/balances {\"Ann\":0,\"Bob\":0}; next valid expense -> 201 {\"expense\":1}",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Safe-integer bound on amounts and resulting balances (400 when a balance would exceed 2^53-1)",
   "where": "server.js balancesFit, maxCents",
   "worth": "value",
   "why": "keeps balances exact; JSON numbers beyond that would silently lose precision"
  },
  {
   "what": "Whole-cent check on the number as written on the wire (1.00000000000000001 rejected, 1e2 / 10e-1 accepted)",
   "where": "server.js readNumberSources, isWholeCent",
   "worth": "neutral",
   "why": "stricter than needed; adds subtle code for an edge few clients reach"
  },
  {
   "what": "Startup validation of PORT, missing DATA_FILE, missing parent directory, and full validation of the saved snapshot",
   "where": "server.js main, loadGroups, validSavedExpense",
   "worth": "value",
   "why": "refuses bad configuration or corrupt data instead of overwriting it"
  },
  {
   "what": "Group ids \".\" and \"..\" reserved",
   "where": "server.js isGroupId",
   "worth": "neutral",
   "why": "avoids path-normalising clients; harmless"
  },
  {
   "what": "README with API table, validation rules and persistence guarantees",
   "where": "README.md",
   "worth": "value",
   "why": "accurate account of the behaviour observed"
  },
  {
   "what": "Ledger file created with mode 0600",
   "where": "server.js saveGroups",
   "worth": "neutral",
   "why": "private by default; not requested"
  }
 ],
 "spec_notes": "No contradictions of the request. Every stated item has a clause. Choices the request leaves open are mostly marked \"Open:\" (malformed-JSON status, id rules, duplicate/whitespace members, crash recovery, corrupt DATA_FILE, 400 vs 409 precedence) or tagged \"Source: implied\" (absent DATA_FILE, omitted exact members owe zero, concurrent create race, numbering after restart, settlements read-only). Some decisions sit in ordinary \"Source: request\" lines though the request does not say them: C-14 rejects a string \"4\" for cents, C-21 rejects negative and string shares, C-20 rejects a non-member even with a zero share, C-8 rejects a non-list members value. The spec pins exact worked examples (balances and settlement arrays) that any correct build shares; it does not pin the storage layout or the startup message.",
 "tests_notes": "Six broad tests, each covering many behaviours (the first covers port, member validation, duplicate 409, preservation and the create race; the third covers about twenty rejections), so a failure name does not locate the broken rule. The harness waits for the stdout line \"Listening on port N\" and reads the port from it: another correct build that prints nothing or another message would fail every test. The whole-cents test expects 400 for 1.00000000000000001 and for a share of 1e-500, and 201 for 10e-1: a correct build that reads JSON numbers normally would accept the first (it parses to 1) and fail. Restart is only tested after a graceful SIGTERM; no test kills mid-write, sends malformed-JSON status assertions, odd group ids, or a corrupt DATA_FILE.",
 "maintainer": "The number handling is the most fragile part: readNumberSources re-parses the body with the JSON.parse reviver source context (with a regex fallback for older Node that this Node 26 run never exercises) and isWholeCent does decimal-string arithmetic, so a change there can silently accept or reject amounts. Persistence rewrites the whole snapshot through one global commit queue and replies only after the rename; any change to storage must keep that ordering, and loadGroups/validSavedExpense tie the on-disk format (per-expense shares arrays in member order) to the code, so a layout change breaks existing ledgers."
}
```

## Audit of delivery Z

```json
{
 "code": "Z",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "node server.js (PORT=47311 DATA_FILE=.audit/p1.json) printed \"Listening on port 47311\" and answered every probe; the product is server.js plus test/, no other runtime files.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Renamed server.js to app.js: all 5 tests fail (TC-1..TC-5: server exited before listening). Renamed back; suite 5/5 pass."
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "No package.json, no node_modules; server.js requires only node:fs, node:http, node:path, node:crypto; it runs with plain `node server.js`.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47311 -> \"Listening on port 47311\" and requests to 127.0.0.1:47311 answered; tests use PORT=0 and the logged port.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "With DATA_FILE=.audit/p1.json the file appears on the first write and holds {\"groups\":[[\"g\",{\"members\":[...],\"expenses\":[...]}],...]}; it is valid JSON.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed `path.resolve(dataFile)` to `path.resolve(dataFile + '.x')`: TC-4 and TC-5 fail. Restored; suite 5/5 pass."
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "After SIGTERM and restart with the same DATA_FILE: POST /groups {\"id\":\"g\",...} -> 409 and GET /groups/g/balances -> 200 with the same values.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "Before restart GET /groups/g/balances -> {\"Ann\":-2,\"Bob\":56,\"Cy\":-54}; after restart identical, and the next expense got number 5.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\",\"Bob\",\"Cy\"]} -> 201 {\"id\":\"g\"}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups {\"id\":\"g\",\"members\":[\"Ann\",\"Bob\"]} again -> 409 {\"error\":\"Group already exists.\"} (also after restart).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\"] -> 400, [] -> 400 {\"error\":\"Provide at least two distinct member names.\"}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\",\"Ann\"] -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed `new Set(members).size < 2` to `members.length < 2` ([\"Ann\",\"Ann\"] then 201): TC-1 fails. Restored; suite 5/5 pass."
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "members [\"Ann\",\"\"] -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups/g/expenses {\"payer\":\"Ann\",\"cents\":100,\"split\":\"equal\"} -> 201 {\"expense\":1}; balances credit Ann the 100 paid.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "Group Ann,Bob,Cy; Ann pays 100 equal -> balances {\"Ann\":66,\"Bob\":-33,\"Cy\":-33} (shares 34/33/33).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "Members Zoe,Yan,Xu, Xu pays 101 equal -> {\"Zoe\":-34,\"Yan\":-34,\"Xu\":68}; members A,B,C,D, D pays 7 -> {\"A\":-2,\"B\":-2,\"C\":-2,\"D\":6}: leftover cents go to the first-listed.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "Bob pays 90 exact {\"Ann\":60,\"Cy\":30} -> 201 {\"expense\":2}; balances moved by exactly those shares (Ann -60, Cy -30, Bob +90).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "Cy pays 10 exact {\"Ann\":10,\"Bob\":0} -> 201 {\"expense\":3}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "Ann pays 100 exact {\"Ann\":50,\"Bob\":40} -> 400 {\"error\":\"Invalid expense.\"}; {\"Ann\":60,\"Bob\":50} -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Replaced `return remaining === 0 ? { payerIndex, cents, amounts } : null;` with `return { payerIndex, cents, amounts };`: TC-2 fails. Restored; suite 5/5 pass."
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "Every recorded expense answered 201 with body exactly {\"expense\":n}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "Group g: 1, 2, 3, then after eight 400s the next was 4; each new group starts at 1 (r, r2, t, u).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "payer \"Zed\" -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "exact shares {\"Ann\":50,\"Zed\":50} -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "cents 0 -> 400; cents -5 -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed `cents <= 0` to `cents < 0` (cents 0 then 201): TC-2 fails. Restored; suite 5/5 pass."
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "cents 10.5 -> 400; cents 2^53 -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "split \"percent\" -> 400.",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "Changed `if (split === 'equal') {` to `if (split !== 'exact') {` (unknown split treated as equal): TC-2 fails. Restored; suite 5/5 pass."
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "shares adding to 90 or 110 for cents 100 -> 400.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/balances -> 200 {\"Ann\":-2,\"Bob\":56,\"Cy\":-54}, one key per member, integer cents; empty group -> {\"A\":0,\"B\":0}.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "Hand check of group g after 4 expenses: Ann paid 103 owes 105 = -2, Bob paid 90 owes 34 = 56, Cy paid 10 owes 64 = -54; matches.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "Every balances body observed summed to 0 (g: -2+56-54; u: 40-20-30-50+60; big: +/-18014398509481982).",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "GET /groups/g/settlements -> 200 [{\"from\":\"Cy\",\"to\":\"Bob\",\"cents\":54},{\"from\":\"Ann\",\"to\":\"Bob\",\"cents\":2}]; empty group -> [].",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "Applying the payments to the balances of g, t and u leaves every member at 0.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "Group u balances A40,B-20,C-30,D-50,E60 -> [D->E 50, C->A 30, B->A 10, B->E 10], the largest-debtor/largest-creditor/smaller-amount sequence by hand.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "Group t balances A100,B100,C-100,D-100 -> [C->A 100, D->B 100]; group u creditors A10/E10 tie -> B pays A first.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "POST /groups/nope/expenses (valid and non-JSON body), GET /groups/nope/balances, GET /groups/nope/settlements -> 404 each.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "100 concurrent POST /groups/g/expenses (2 cents equal) -> 100x201, numbers exactly 1..100, balances {\"Ann\":100,\"Bob\":-100}; under SIGKILL mid-stream every acknowledged expense was present after restart (5 rounds).",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "`node --test` from the project root runs test/expenses.test.js: 5 tests, 5 pass, exit 0.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Unparseable body -> 400 with an error message; nothing stored; server keeps serving.",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups raw \"{\" -> 400 {\"error\":\"Invalid group id.\"}; \"not json\" -> 400; POST /groups/g/expenses \"not json\" -> 400 {\"error\":\"Invalid expense.\"}; empty body -> 400; then POST /groups g9 -> 201 and GET /groups/g/balances -> {\"Ann\":0,\"Bob\":0}.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "Every missing field -> 400; nothing stored.",
   "handling": "sound",
   "observed": true,
   "evidence": "expenses {} / no split / no payer / no cents / exact without shares / null -> 400 each; POST /groups {} -> 400, {\"id\":\"h\"} -> 400; g balances still {\"Ann\":0,\"Bob\":0}; /groups/h/balances -> 404.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Wrong types refused with 400, no coercion (number literals 1e2 and 100.0 are the integer 100 and accepted).",
   "handling": "sound",
   "observed": true,
   "evidence": "members \"Ann,Bob\" -> 400; [\"Ann\",7,\"Bob\"] -> 400; cents \"100\" -> 400; shares [100] -> 400; share \"50\" -> 400; cents true -> 400; payer 7 -> 400; g2 balances unchanged by refused posts.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "Non-empty, non-blank string ids accepted; \"\", missing, numeric and \" \" rejected 400; every accepted id reachable percent-encoded by all three routes.",
   "handling": "sound",
   "observed": true,
   "evidence": "ids \"a/b\" (a%2Fb), \"a b\" (a%20b), \"50%\" (50%25), \"café\" (caf%C3%A9), \"a?b\" (a%3Fb), \"..\", \"%41\" (%2541): each 201 then balances 200, settlements 200, POST expense 201, balances {\"A\":5,\"B\":-5}. \"\", none, 1, \" \" -> 400.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "Negative and fractional shares -> 400; balances stay whole and zero-sum.",
   "handling": "sound",
   "observed": true,
   "evidence": "{\"Ann\":150,\"Bob\":-50} -> 400; {\"Bob\":-50,\"Ann\":150} -> 400; {\"Ann\":50.5,\"Bob\":49.5} -> 400; balances {\"Ann\":0,\"Bob\":0}.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-6",
   "behaviour": "Repeated names accepted and de-duplicated in first-listed order; whitespace-only names rejected; case and surrounding-space variants are distinct members.",
   "handling": "sound",
   "observed": true,
   "evidence": "[\"Ann\",\"Ann\",\"Bob\"] -> 201, Ann pays 100 equal -> {\"Ann\":50,\"Bob\":-50}; [\"Ann\",\" \",\"Bob\"] -> 400; [\" \",\"Bob\"] -> 400; [\"Ann\",\"ann\"] -> 201 {\"Ann\":0,\"ann\":0}; [\" Ann\",\"Ann\"] -> 201 with two members.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-8",
   "behaviour": "Writes to a temporary file in the same directory then renames before replying; acknowledged writes survive SIGKILL and the file always parsed. A kill mid-write can leave a stray .expenses-<uuid>.tmp beside the file.",
   "handling": "sound",
   "observed": true,
   "evidence": "SIGKILL right after a 201: restart balances {\"Ann\":5,\"Bob\":-5}, file parses. 5 rounds of 8 looping clients killed mid-stream: acked 884/1062/1176/1226/1300, file parsed each time and Ann's delta equalled the acked count exactly. One stray .expenses-ffbde199-....tmp left in the data directory.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "Starts with an empty store; the file is created on the first successful write; group found after restart. (If the directory itself is missing it starts and answers 500 to every write.)",
   "handling": "sound",
   "observed": true,
   "evidence": "DATA_FILE=.audit/p3.json absent: started, file absent at start, present after POST /groups; after restart race and g groups present. Missing directory: started; POST /groups -> 500 {\"error\":\"Request could not be completed.\"}.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-10",
   "behaviour": "Invalid JSON or an empty file: refuses to start (exit 1, SyntaxError stack on stderr) and leaves the file untouched.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "\"{broken\" -> exit 1 \"SyntaxError: Expected property name or '}' in JSON at position 1\"; file still \"{broken\". Empty file -> exit 1 \"Unexpected end of JSON input\"; file still \"\". The error is a raw stack, not a message naming DATA_FILE.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-13",
   "behaviour": "Each concurrent post gets a distinct number 1..N and is applied once.",
   "handling": "sound",
   "observed": true,
   "evidence": "100 concurrent POST {\"payer\":\"Ann\",\"cents\":2,\"split\":\"equal\"} -> 100x201, numbers exactly 1..100, balances {\"Ann\":100,\"Bob\":-100}.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-15",
   "behaviour": "Exactly one creation wins; the rest get 409; the winner's members are stored and survive restart.",
   "handling": "sound",
   "observed": true,
   "evidence": "20 concurrent POST /groups id \"race\" alternating members: 1x201 (request 0, Cy,Di) and 19x409; balances {\"Cy\":0,\"Di\":0} before and after restart.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-16",
   "behaviour": "Numbering continues after restart.",
   "handling": "sound",
   "observed": true,
   "evidence": "Group g with 130 expenses, restart, next POST -> {\"expense\":131}; group k after restart -> 3; p1 group g -> 5 after 4.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "409 (existence checked before members); stored members unchanged.",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /groups g21 [\"Ann\",\"Bob\"] -> 201; POST g21 [\"Ann\"] -> 409; balances {\"Ann\":0,\"Bob\":0}.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-25",
   "behaviour": "GETs only read; identical bodies and the file is not rewritten.",
   "handling": "sound",
   "observed": true,
   "evidence": "balances twice {\"Ann\":50,\"Bob\":-50}; settlements twice [{\"from\":\"Bob\",\"to\":\"Ann\",\"cents\":50}]; DATA_FILE mtime and content unchanged.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "Stored state reads back identically; next number continues.",
   "handling": "sound",
   "observed": true,
   "evidence": "Group k with equal and exact expense: balances {\"Ann\":66,\"Bob\":17,\"Cy\":-83} and settlements [Cy->Ann 66, Cy->Bob 17] identical after restart; next expense -> 3. File: {\"groups\":[[\"k\",{\"members\":[...],\"expenses\":[{\"payerIndex\":0,\"cents\":100,\"amounts\":[34,33,33]},...]}]]}.",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-27",
   "behaviour": "Tests spawn server.js on PORT=0 with a temporary DATA_FILE under os.tmpdir(), remove it and stop the child.",
   "handling": "sound",
   "observed": true,
   "evidence": "`node --test` twice -> exit 0, 5/5; again with another process holding port 3000 -> exit 0; no new files in the project folder (find diff empty); no shared-expenses-* temp dirs from these runs; no node process left.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-31",
   "behaviour": "A group creation and an expense in another group sent together both persist.",
   "handling": "sound",
   "observed": true,
   "evidence": "30 rounds of concurrent POST /groups h<i> and POST /groups/g/expenses: all 201; after restart all 30 h groups {\"Cy\":0,\"Di\":0} and g balances reflect all 30 expenses ({\"Ann\":70,\"Bob\":-70}).",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-35",
   "behaviour": "Aborted body: nothing stored, \"Request failed: aborted\" on stderr, server keeps serving.",
   "handling": "sound",
   "observed": true,
   "evidence": "5 sockets sent headers with Content-Length 1000 and a partial body then closed; balances {\"Ann\":0,\"Bob\":0}; next valid expense -> 201 {\"expense\":1}.",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Exact BigInt aggregation with JSON.rawJSON output for totals beyond 2^53",
   "where": "server.js balancesFor/send",
   "worth": "neutral",
   "why": "Correct at extreme totals, but needs a Node with JSON.rawJSON and clients with a precision-preserving parser; not asked."
  },
  {
   "what": "Startup validation of PORT and DATA_FILE",
   "where": "server.js top",
   "worth": "value",
   "why": "Fails fast with a message when either is missing or PORT is not a valid port."
  },
  {
   "what": "Write failure answers 500 and leaves the in-memory state unchanged so a retry works",
   "where": "server.js saveGroup; TC-5",
   "worth": "value",
   "why": "No acknowledged-but-unsaved expense and no consumed number on failure."
  },
  {
   "what": "Data file and temp files written with mode 0600",
   "where": "server.js saveGroup",
   "worth": "neutral",
   "why": "Restricts the ledger to the owner; harmless."
  }
 ],
 "spec_notes": "The spec (docs/[tool]/spec.md) does not contradict the request. It does not state S-28 (balances sum to 0). It decides several unsaid points in ordinary requirement lines without marking them as the builder's choice: repeated member names collapse to one member in first-occurrence order, shares must be nonnegative safe whole cents, inputs must be safe integers, and aggregates are \"emitted as exact JSON integers\" (pins the BigInt/JSON.rawJSON choice, which another correct build need not share). It is silent on an absent, empty or corrupt DATA_FILE, unparseable bodies, the 400-vs-409 order, concurrent creation of one id, and whether GETs write. No customer-facing README or API document was delivered; the only documents are the builders' spec and working notes, so nothing is told to a customer.",
 "tests_notes": "Five tests, each covering many behaviours: TC-2 alone checks remainder order, exact shares, 17 invalid inputs, numbering and BigInt totals, so one failure hides the rest. Tied to internals or to this build's choices: the fixture parses the exact stdout line \"Listening on port N\"; TC-5 forces a write failure by replacing the data file with a directory (depends on the write-then-rename mechanism); TC-2 expects exact BigInt totals above 2^53 and 201 for MAX_SAFE_INTEGER expenses; TC-1 expects 201 for a member list with a repeated name and 400 for a whitespace-only name, and TC-2 expects 400 for cents \"10\" - another correct build that rejects repeats, accepts blank-looking names or coerces \"10\" would fail. No test covers corrupt/empty DATA_FILE, concurrent group creation, exact expenses across restart, settlements after restart, or GETs being read-only. S-3 is only weakly covered (tests read the logged port).",
 "maintainer": "Concurrency safety rests on there being no await between reading a group and the synchronous saveGroup in the expense route (a comment marks it); switching to fs.promises or adding any async step there would silently reintroduce lost expenses. Expenses are stored by member index (payerIndex, amounts[]), so any future change to a group's member list would corrupt history, and the whole file is rewritten on every write. Everything (routing, validation, ledger, persistence) lives privately in one server.js and is testable only through spawned processes."
}
```

