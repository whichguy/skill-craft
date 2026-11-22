# Answer for run s1

## A. The start-up question: partly

Row 4 is about this. It says: "At the first start of the new release, whatever DUE_TIMES says, using the hours set at that moment; the file is rewritten once with no audit entries." It names another answer: "A separate migration command run by operators before the switch; it adds a step that can be forgotten."

Why only partly:
- Who fills the due times in is only implied ("the first start of the new release"). The row never says the service itself does it.
- The row never says what a start with DUE_TIMES on does when some ticket has no due time. That case arises, for example, after a rollback to 1.4.0 and a second upgrade. The only hint is "whatever DUE_TIMES says". Row 5 mentions the second upgrade ("the next upgrade recomputes them") but not an enabled start.
- "the file is rewritten once with no audit entries" is wording about the mechanism, not about what the person running the service sees.

What the specification requires: R-6 says "When the service loads a data file, every ticket without `due` gets created + hours(priority) under the hours in force then, and the file is saved at start so it holds them". R-7 adds "Whatever DUE_TIMES says, the service computes and stores `due`". So the service fills in every missing due time on every start, whether DUE_TIMES is on or off, and an enabled start never meets a ticket without one.

## B. Each row

1. R-2 how hours are changed: open. The request says only "without a code change". R-2 states "Environment variables DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL, DUE_HOURS_LOW ... unset or empty takes the default", and "DUE_HOURS_HIGH=abc or 0 stops the service at start with a message naming the variable". The 1 to 100000 range is also in R-2.
2. R-5 due exactly now, and overdue=false: open. The request says only "whose due time has passed". R-5 states "due is strictly before now" and "`overdue=false` or any other value than `true` is 400 `invalid`".
3. R-7 DUE_TIMES unset, off or misspelt: open. The request says "until the DUE_TIMES environment variable is `on`", but not what a misspelling does. R-7 states "Without `on`: no response body has `due`, and `overdue` is ignored". The word "exact" is in R-4: "only the exact value `on` switches on; anything else ... is off". R-7 also states "the service computes and stores `due`". The clause for the named requirement is thinner than the row, but the content is in the specification.
4. R-6 when existing tickets get due times, and with which hours: open. The request does not say when or by what route. R-6 states "When the service loads a data file ... under the hours in force then, and the file is saved at start ... No audit entry". R-7 states "Whatever DUE_TIMES says".
5. R-8 what rollback loses: open. The request does not say whether due times must survive a rollback. R-8 states "1.4.0 re-saves without `due`; upgrading again backfills from the then-current hours". It also states "`due` an additive optional ticket field that 1.4.0 ignores", which excludes the side file the row offers as the alternative.
6. R-2 largest hours accepted: added. The request asks for no limit. R-2 states "a whole number from 1 to 100000 (about 11 years ...)" and "100001 are refused at start". The stated reason, a valid date, shows the bound is a robustness extra and not something the request needs. This is borderline: it could be read as open. Row 1 already carries the same bound ("Each value must be a whole number from 1 to 100000 hours"), so row 6 repeats row 1.

## C. Choices the specification made that no row mentions

- A `due` that is present but not a time is refused at load, naming the record. This is in R-6, Failure.
- The backfill and its save happen when the service opens the store, not in the loader that bin/tickets.js and scripts/weekly-report.js use. Those never write the data file. This is in R-6, Preserved. R-7 adds that the command line and weekly report print what they print today.
- `overdue=true` narrows whatever else the listing returns. It is not part of the existing OR of status and priority, and paging works on the narrowed list. This is in R-5, Combination.
- An empty DUE_HOURS value counts as unset and takes the default. This is in R-2. Row 1 says only "unset".

Not counted, but present: R-2 implies that a bad DUE_HOURS value stops the start even with DUE_TIMES off. The specification never says so outright.

## D. In a row but not in the specification

Nothing contradicts the specification. Two small points are beyond its wording:
- Row 1 says the operator restarts the service after setting the variables. R-2 says only that bad values stop it "at start", so a restart is implied.
- Row 4 says "rewritten once". R-6 says "saved at start" and does not say how many times the file is rewritten.

A: partly; rows: 6 (open 5, settled 0, added 1, unstated 0); missed: 4
