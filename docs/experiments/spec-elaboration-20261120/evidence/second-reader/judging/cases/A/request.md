# Request

ShipLoop writes this file from the run's request: the request verbatim, then the same text split into sentences S1..Sn. The split is a display index for citing a sentence (S<n>); the verbatim text governs. The intake, spec and plan packets quote it too; every other packet names this file.

## Verbatim

~~~text
This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. The help desk is starting to promise response times. Each ticket gets a due time: the time it was created plus the response time for its priority, which is 4 hours for urgent tickets, 24 for high, 72 for normal and 168 for low, and the help desk must be able to change those hours without a code change. A ticket's due time is set once: a later change of the hours or of the ticket's priority does not move it. Every ticket shows its due time as `due`, and `GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed. The tickets already in the production data file get due times too, from their own creation time and priority, and keep them from then on. Due times are switched on in production only once the data file holds them: until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today. If the new release misbehaves, operators must be able to go back to the current release, 1.4.0, and it must still start on the data file the new release wrote and show every ticket. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.
~~~

## Sentences

- S1: This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/.
- S2: The help desk is starting to promise response times.
- S3: Each ticket gets a due time: the time it was created plus the response time for its priority, which is 4 hours for urgent tickets, 24 for high, 72 for normal and 168 for low, and the help desk must be able to change those hours without a code change.
- S4: A ticket's due time is set once: a later change of the hours or of the ticket's priority does not move it.
- S5: Every ticket shows its due time as `due`, and `GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed.
- S6: The tickets already in the production data file get due times too, from their own creation time and priority, and keep them from then on.
- S7: Due times are switched on in production only once the data file holds them: until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today.
- S8: If the new release misbehaves, operators must be able to go back to the current release, 1.4.0, and it must still start on the data file the new release wrote and show every ticket.
- S9: Everything the service already does keeps working, and its existing tests must still pass as they are.
- S10: Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.
