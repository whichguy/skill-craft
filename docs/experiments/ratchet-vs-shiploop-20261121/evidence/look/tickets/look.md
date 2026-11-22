# Delivered ticket assignment review

## Shortfalls

Run the examples from the repository root with two new tickets. Use a free port and keep the worker on for the notification check.

```sh
run=$(mktemp -d "$PWD/../tmp/tickets-look.XXXXXX")
export PORT=45673 DATA_FILE="$run/tickets.json" NOTIFY_FILE="$run/notifications.jsonl"
export WORKER_INTERVAL_MS=500
node src/server.js > "$run/server.log" 2>&1 &
server_pid=$!
base="http://127.0.0.1:$PORT"
api() { curl -sS -w '\nHTTP %{http_code}\n' -H 'Content-Type: application/json' "$@"; }
assign() { api -X PUT -d "$1" "$base/tickets/$2/assignee"; }

# Once GET /health answers 200, create T-0001 and T-0002.
api -d '{"title":"VPN","requester":"maria@example.com"}' "$base/tickets"
api -d '{"title":"Printer","requester":"maria@example.com"}' "$base/tickets"
# After the examples, stop the service with kill "$server_pid" and wait "$server_pid".
```

### Repeated assignee filters return tickets that fail the second filter — high

```sh
assign '{"assignee":"Dana Lee"}' T-0001
assign '{"assignee":"Kim"}' T-0002
api "$base/tickets?assignee=Dana%20Lee&assignee=Kim"
```

The request returned HTTP 200 with `T-0001` and `next: null`. The two filters are incompatible, so the result should contain no tickets. Appending a filter to a URL that already has one can silently show the wrong agent's queue.

### Operators have no documented route from an agent name to a notification destination — medium

After the two assignments above, wait for the worker and inspect the handoff.

```sh
rg '"type":"ticket.assigned","to":"Dana Lee"' "$NOTIFY_FILE"
api "$base/admin/outbox"
```

The JSONL record for `T-0001` had subject `[T-0001] Assigned to you` and `"to":"Dana Lee"` as its only recipient field. The outbox reported the event in `sent`. The delivered operations instructions tell the operator which file the mail relay tails. To notify someone using the documented name example, the operator also needs a routable destination or instructions for resolving that name at the relay. The local check reached the relay handoff. Mailbox receipt was unverified.

### The CLI displays an accepted assignee as unassigned — high

```sh
assign '{"assignee":"—"}' T-0001
assign '{"assignee":null}' T-0002
node bin/tickets.js list
```

Both writes returned HTTP 200. The API stored the name `"—"` on `T-0001` and `null` on `T-0002`. The CLI printed `—` in both assignee cells, which the README tells operators to interpret as unassigned. Operators should be able to distinguish a stored name from the unassigned marker.

### Unicode line breaks pass the single-line check and split raw CLI records — medium

```sh
assign '{"assignee":"Dana\u2028Lee"}' T-0001
assign '{"assignee":"Dana\u2029Lee"}' T-0001
assign '{"assignee":"Dana\u0085Lee"}' T-0001
node bin/tickets.js list --raw | python3 -c 'import sys; print(ascii(sys.stdin.read().splitlines()))'
```

All three writes returned HTTP 200. The line reader returned three records for two tickets, including a standalone `Lee` after the row ending in `Dana`. The API should reject these embedded line breaks with HTTP 400, as it does for an embedded newline, so accepted names preserve the documented one-line-per-ticket output.

### An accepted assignee can be impossible to filter for — low

```sh
assign '{"assignee":"\uD800"}' T-0001
api "$base/tickets?assignee=%ED%A0%80"
api "$base/tickets?assignee=%EF%BF%BD"
node bin/tickets.js list --raw
```

The write returned HTTP 200 and stored the unpaired surrogate as the assignee. The raw CLI rendered it as `�`, and both the attempted encoding of the stored value and the query for the displayed value returned HTTP 200 with no items. The API should reject the malformed name with HTTP 400 so every stored assignee can be represented in a filter and displayed faithfully.

## Choices the customer was not told

- An impossible assignee search value, such as a 65-character name or a name with a tab, returns HTTP 200 with an empty page. A bare `?assignee` works like `?assignee=`.
- Lifecycle transitions retain the last assignee through resolution, closure, and reopening. Reopening leaves the assignment notification history as it was.
- Unassigning creates no notification of its own. A pending notice still goes to the original recipient if the ticket is unassigned or reassigned before the worker runs.
- A delayed assignment notice uses the ticket title as it was when the assignment was made, even if the title changes before delivery.
