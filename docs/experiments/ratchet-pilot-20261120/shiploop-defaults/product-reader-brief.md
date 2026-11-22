# The product reader's brief for R6 (and the stale-row check of R4)

Given to a reader per run, with that run's delivered product folder and the rows it printed. Written before any run
of the candidate (DESIGN.md section 3). The reader does not see the held-out checks or their results.

You are given:

1. `PRODUCT`: a folder holding a small Node.js help-desk ticket service as one delivery run left it (source under
   `src/`, a command-line tool under `bin/`, documents, tests).
2. `ROWS`: a numbered list that run printed for the person who made the request: for each row a requirement (R-<n>),
   a question the request left open, what was decided, and one other answer. It may be empty.

The request the run worked from asked for due times on tickets: created time plus a response time by priority (4, 24,
72 and 168 hours for urgent, high, normal and low), hours the help desk can change without a code change, a due time
set once and never moved, `due` shown on every ticket, `GET /tickets?overdue=true`, due times for the tickets already
in the production data file, a switch (`DUE_TIMES=on`) before which the service answers exactly as today, and a way
back to release 1.4.0 on the file the new release wrote.

Read the product's source and documents (you may read any file under PRODUCT and nothing else, and run nothing).
Answer from what the code does, quoting the file and the lines you rely on.

**1. What the product does on these points.** One or two sentences each:

a. How the help desk changes the hours (which setting, where, and when it takes effect).
b. What an invalid setting of the hours does.
c. Whether there is a largest number of hours the product accepts, and what it is.
d. Who or what gives the tickets already in the data file their due times, and when.
e. What the service does when it is started with `DUE_TIMES=on` while some ticket in the file has no due time.
f. Whether a ticket due exactly now counts as overdue.
g. Any other limit, refusal or operator step the product has for this feature that the request does not mention.

**2. Against the rows.** For each of a to g: is there a row that tells the requester this? `row <n>` or `no row`.
For each row: does the product do what the row says was decided? `as the row says`, `differs` (say how), or
`cannot tell`.

End with two lines:
`not in any row: <the letters>`
`rows the product contradicts: <the row numbers, or none>`
