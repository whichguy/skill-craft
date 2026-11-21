## Use cases

### U-1: A salesperson asks the bot about a record they are looking at
Flow: They open the record, type a question, and the answer appears beside the record.
Source: request

### U-2: An administrator deploys the bot from the development org onward
Flow: They build in a scratch org, run the tests, and deploy the metadata to a sandbox and then production.
Source: implied: a development org is not where it stays

## Clauses

### C-1: The bot answers only from records the asking user can already see
Observable: A user who cannot open an account in the user interface gets no content from that account in an answer; the answer says it found nothing it could show them.
Source: implied: by U-1

### C-2: The model call runs asynchronously, never inline in the user's transaction
Observable: Submitting a question returns at once with the question in a pending state; the answer arrives afterwards. Apex forbids a callout after DML in one transaction and caps a callout at 120 seconds, so the call is enqueued rather than made in line.
Source: implied: the platform forbids the inline form

### C-3: The API credential is held in a Named Credential and never appears in code, metadata or a log
Observable: Searching the deployed metadata and the debug logs for the key returns nothing; rotating the credential needs no code change.
Source: implied: by C-2

### C-4: A re-enqueued or retried job never posts the same answer twice
Observable: Forcing the job to run twice for one question leaves exactly one answer record on the conversation.
Source: implied: by C-2

### C-5: A refusal, a failure and a timeout each give a different visible outcome
Observable: A 4xx refusal shows that the question could not be accepted; a 5xx failure shows that the service is unavailable and the question will be retried; a timeout shows that the answer did not arrive in time and offers to ask again.
Source: implied: by U-1

### C-6: A conversation and its turns are stored as records
Observable: Each conversation holds its turns in order, each turn carrying its role, its text, its status, its timestamp and the model identifier that produced it.
Source: implied: by U-1

### C-7: The Apex tests use a mocked callout
Observable: The test suite passes with no network access, because the HTTP callout is supplied by a mock implementation.
Source: implied: by C-2

### C-8: The bot's configuration differs per environment
Observable: The development org, the sandbox and production each resolve their own endpoint and credential without a code change, and the deployment to production meets the platform's code-coverage requirement.
Source: implied: by U-2
