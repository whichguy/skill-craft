# Shared-expenses delivery review

## Shortfalls

The commands below run from the repository root using Bash, Node and curl. Each example uses a separate ledger and an OS-assigned port.

```sh
run=$(mktemp -d "$PWD/../tmp/look-repro.XXXXXX")
start() {
  PORT=0 DATA_FILE="$1" node server.js > "$1.log" 2>&1 &
  pid=$!
  for attempt in {1..100}; do
    port=$(awk '/^Listening on port / {print $4; exit}' "$1.log")
    if [ -n "$port" ]; then
      base="http://127.0.0.1:$port"
      return
    fi
    sleep 0.05
  done
  cat "$1.log"
  stop "$pid"
  return 1
}
stop() { kill "$1" 2>/dev/null; wait "$1" 2>/dev/null || true; }
post() { curl -sS --max-time 5 -w '\n%{http_code}\n' -H 'Content-Type: application/json' --data-binary "$2" "$base$1"; }
get() { curl -sS --max-time 5 -w '\n%{http_code}\n' "$base$1"; }
```

### Fractional amounts enter the ledger as whole cents (`high`)

The API needs to reject fractional totals and shares and leave the ledger unchanged. Send the numeric literals directly so the client preserves the original digits.

```sh
start "$run/money.json"
post /groups '{"id":"trip","members":["Ada","Bea","Cam"]}'
post /groups/trip/expenses '{"payer":"Ada","cents":1.5,"split":"equal"}'
post /groups/trip/expenses '{"payer":"Ada","cents":0.99999999999999999,"split":"equal"}'
post /groups/trip/expenses '{"payer":"Ada","cents":2,"split":"exact","shares":{"Bea":2.0000000000000001}}'
post /groups/trip/expenses '{"payer":"Ada","cents":2,"split":"exact","shares":{"Bea":2,"Cam":-1e-400}}'
get /groups/trip/balances
stop "$pid"
```

The first expense request returned 400, as expected. The next three returned 201 with expense numbers 1, 2 and 3. The total below one cent rounded to 1, the share above 2 rounded to 2, and the negative share rounded to zero. Balances returned 200 with `{"Ada":4,"Bea":-4,"Cam":0}`. Each of those three requests should return 400, with all balances still zero.

### A second process can erase an acknowledged expense (`high`)

The notes assume a single writer per file. An overlapping launch against that file needs to preserve acknowledged expenses, which could be achieved by refusing the second writer.

```sh
start "$run/shared.json"
post /groups '{"id":"trip","members":["Ada","Bea"]}'
first_pid=$pid
first_base=$base
start "$run/shared.json"
BASE1="$first_base" BASE2="$base" node <<'JS'
Promise.all([[process.env.BASE1, 4], [process.env.BASE2, 7]].map(async ([base, cents]) => {
  const response = await fetch(base + '/groups/trip/expenses', {
    method: 'POST',
    body: JSON.stringify({payer: 'Ada', cents, split: 'exact', shares: {Bea: cents}}),
  });
  console.log(cents, response.status, await response.text());
}));
JS
stop "$pid"
stop "$first_pid"
start "$run/shared.json"
get /groups/trip/balances
post /groups/trip/expenses '{"payer":"Ada","cents":2,"split":"equal"}'
stop "$pid"
```

Both writes returned 201 with `{"expense":1}`. After restarting, balances showed `{"Ada":7,"Bea":-7}` and the next expense got number 2. The last file replacement wins, so either original expense can disappear. If both writes are acknowledged, balances should be 11 and −11 before the next expense, with number 3 available.

### An unrelated JSON file is silently overwritten (`high`)

An operator who points `DATA_FILE` at an existing file without a ledger needs a clear failure that preserves the file.

```sh
printf '%s\n' '{"unrelated":["keep me"]}' > "$run/wrong.json"
start "$run/wrong.json"
post /groups '{"id":"new","members":["Ada","Bea"]}'
cat "$run/wrong.json"
stop "$pid"
```

The process announced it was listening, the POST returned 201 with `{"id":"new"}`, and the original contents were replaced with `{"groups":[["new",{"members":["Ada","Bea"],"expenses":[]}]]}`. The process should reject the unexpected contents and leave the existing file intact.

### Some created groups cannot be used through ordinary URLs (`medium`)

A 201 from group creation should leave a group callers can use for expenses, balances and settlements. Otherwise creation should return 400.

```sh
start "$run/ids.json"
post /groups '{"id":".","members":["Ada","Bea"]}'
post /groups '{"id":"..","members":["Ada","Bea"]}'
BASE="$base" node <<'JS'
Promise.all(['.', '..', '%2E', '%2E%2E'].map(async id => {
  const url = new URL('/groups/' + id + '/balances', process.env.BASE);
  const response = await fetch(url);
  console.log(id, url.pathname, response.status);
}));
JS
curl -sS --path-as-is -w '\n%{http_code}\n' "$base/groups/./balances"
post /groups '{"id":"\ud800","members":["Ada","Bea"]}'
get /groups/%ED%A0%80/balances
get /groups/%EF%BF%BD/balances
for n in 16000 16500; do
  id=$(node -e 'process.stdout.write("a".repeat(Number(process.argv[1])))' "$n")
  post /groups "{\"id\":\"$id\",\"members\":[\"Ada\",\"Bea\"]}" | tail -n 1
  get "/groups/$id/balances"
  post "/groups/$id/expenses" '{"payer":"Ada","cents":2,"split":"equal"}'
done
stop "$pid"
```

- The server created `.` and `..` with 201. Node's URL parser collapsed the dot segments, including the percent-encoded forms, and fetch got 404. A raw path sent with curl's `--path-as-is` reached the group and returned 200.
- The lone surrogate `\ud800` also got 201. It has no valid UTF-8 URL encoding. Both the attempted surrogate bytes and the replacement character URL returned 404.
- Both long ASCII IDs got 201. The 16,000-character ID worked for balances and expense creation. The same routes returned 431 for the 16,500-character ID, even when that group was empty.

### Saving through a symlink leaves the ledger target stale (`medium`)

An operator using a stable symlink for `DATA_FILE` needs acknowledged updates to go to the linked ledger, or a clear error before writing.

```sh
printf '%s\n' '{"groups":[["old",{"members":["Ada","Bea"],"expenses":[]}]]}' > "$run/target.json"
ln -s target.json "$run/alias.json"
start "$run/alias.json"
get /groups/old/balances
post /groups/old/expenses '{"payer":"Ada","cents":2,"split":"equal"}'
get /groups/old/balances
ls -l "$run/alias.json" "$run/target.json"
stop "$pid"
start "$run/target.json"
get /groups/old/balances
stop "$pid"
start "$run/alias.json"
get /groups/old/balances
stop "$pid"
```

The process initially read the linked group with zero balances. The expense returned 201 with `{"expense":1}` and balances became `{"Ada":1,"Bea":-1}`. The write replaced the symlink with a regular JSON file and left the target unchanged. Restarting with the target path returned zeros for the same group. Restarting with the alias path retained the expense in the replacement file.

## Choices the customer was not told

- Group IDs and member names must contain a non-whitespace character. Identity uses the string as supplied, including case and surrounding whitespace.
- Duplicate names in the creation list collapse to one member at the first occurrence, which sets that member's position for remainders and ties.
- A duplicate group ID takes precedence over invalid members in the same request. Creation returns 409 even when the replacement members are invalid.
- Group creation returns a JSON object containing the ID. Error responses from the application contain a JSON `error` string.
- Route lookup ignores the query string and decodes one percent-encoded ID segment, so an ID such as `room/1` is addressed as `room%2F1`.
- Unsupported methods and extra path segments, including a trailing slash on a balance route, return 404.
- POST bodies are parsed as JSON regardless of the Content-Type. Extra group properties are ignored, and an equal split ignores any supplied shares.
- Individual totals and shares use the JavaScript safe-integer range, with a maximum of 9,007,199,254,740,991 cents.
- Aggregate balances and transfers are emitted as exact JSON numbers even above the safe-integer range. Clients handling those values need a precision-preserving parser.
- Balance and settlement responses that contain amounts require a Node runtime with `JSON.rawJSON`.
- A missing data file is created on the first successful write. Startup can announce a listener before a write exposes a missing parent directory. Invalid JSON syntax in an existing file aborts startup.
- A failed save returns 500 and leaves balances and expense numbering unchanged, so a rejected save can be retried after correcting the file path or permissions.
- Writes replace the ledger with an owner-only file. An existing regular file with mode `0640` became `0600` after a successful write.
- The service listens on the wildcard address, which accepts connections on interfaces beyond loopback.
- `PORT=0` asks the OS to select a port, which the server prints to standard output.
