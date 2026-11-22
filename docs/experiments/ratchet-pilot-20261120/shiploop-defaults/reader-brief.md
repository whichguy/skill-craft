# The reader's brief for R1 and R2

Given to a reader who has not seen the delivered product, the held-out checks or their results. One brief per run,
with that run's two attachments. Written before any run of the candidate (DESIGN.md section 3).

You are given two texts from one software delivery run:

1. `spec.md`: the specification the run wrote for the request below.
2. `rows.txt`: a numbered list the run printed for the person who made the request. Each row names a requirement
   (R-<n>), a question the request leaves open, what was decided, and one other answer. It may be empty.

The request, word for word:

> This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket
> API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in
> bin/. The help desk is starting to promise response times. Each ticket gets a due time: the time it was created plus
> the response time for its priority, which is 4 hours for urgent tickets, 24 for high, 72 for normal and 168 for low,
> and the help desk must be able to change those hours without a code change. A ticket's due time is set once: a later
> change of the hours or of the ticket's priority does not move it. Every ticket shows its due time as `due`, and
> `GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed. The tickets
> already in the production data file get due times too, from their own creation time and priority, and keep them
> from then on. Due times are switched on in production only once the data file holds them: until the DUE_TIMES
> environment variable is `on`, the service answers exactly as it does today. If the new release misbehaves, operators
> must be able to go back to the current release, 1.4.0, and it must still start on the data file the new release
> wrote and show every ticket. Everything the service already does keeps working, and its existing tests must still
> pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing
> ones.

Answer each question from the two texts only. Quote the words you rely on.

**A. The start-up question.** Does a row tell the requester who or what gives the tickets already in the data file
their due times, and what the service does when it is started with DUE_TIMES on while some ticket has none, and name
another answer? Answer exactly one of:

- `yes`: a row states both (who or what fills them in; what an enabled start does while some are missing) in words a
  help-desk manager would understand, and names a different workable answer.
- `partly`: a row is about this, but leaves out the consequence for the person who runs the service, or names no
  other answer, or can only be understood by someone who knows the mechanism.
- `no`: no row is about this.

Also say what the specification itself requires on this point, in one sentence, with the clause you read it from.

**B. Each row.** For every row, one line:

- `open`: the request really does not settle it, and the specification's clause for the named requirement states
  what the row says was decided;
- `settled`: the request or the product as the specification describes it already settles it, so it was not a choice;
- `added`: the row is behaviour the request does not ask for and does not need (a limit, a refusal, a control for an
  operator, a feature);
- `unstated`: the named requirement's clause does not state what the row says was decided.

**C. Anything the specification decided and no row has.** List each choice of the same kind you can find in the
specification that no row mentions (for example how the hours are set, what an invalid setting does, a bound on a
value), with its clause.

**D. Anything in a row that is not in the specification at all.**

End with one line: `A: yes|partly|no; rows: <n> (open <n>, settled <n>, added <n>, unstated <n>); missed: <n>`.
