# Product specification

## Requirements

### R-1 User listing
Requirement: GET /users lists users in id order; name filtering is case-insensitive plain text; page and size validate and paginate the filtered users. GET /users/:id returns a user or 404.
Status: accepted
Current implementation: implemented in src/server.js for GET /users and GET /users/:id
Current verification: passed by test/user-listing.test.js and test/user-teams.test.js

### R-2 Team filtering and disclosure
Requirement: Ada Lovelace and Grace Hopper are in Engineering; Alan Turing is in Support. Team filtering is exact and case-sensitive, combines with name filtering before pagination, and include=team is opt-in on list and detail responses.
Status: accepted
Current implementation: implemented in src/server.js and src/users.js
Current verification: passed by test/user-teams.test.js

### R-3 User summary
Requirement: GET /users/summary returns a JSON object with total and by_team for all users matching the existing name and team filters; it omits empty groups and ignores page, size, include, and other query parameters.
Status: accepted
Current implementation: pending
Current verification: not run

### R-4 CSV export
Requirement: A later task may add CSV export for the user listing after the output format and consumers have been decided.
Status: deferred
Current implementation: not started
Current verification: not run

## History

> As of 2026-10-31: R-3 was accepted; implementation was pending; verification was not run.
