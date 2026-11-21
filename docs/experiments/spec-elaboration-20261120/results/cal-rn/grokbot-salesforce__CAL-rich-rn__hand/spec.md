# Grok bot: specification

## Consumer outcomes

A salesperson asks the bot about a record they are looking at: they open the record, type a question, and the answer
appears beside the record. An administrator deploys the bot from the development org onward: they build in a scratch
org, run the tests, and deploy the metadata to a sandbox and then production.

## Requirements

### R-1: The bot answers only from records the asking user can already see
- Basis: implied by a salesperson asking about a record.
- Acceptance, failure: a user who cannot open an account in the user interface gets no content from that account in
  an answer; the answer says it found nothing it could show them. Surface: the bot's reply. Confirmed by asking as
  that user.
- Acceptance, positive and boundary: n/a: the failure line states the rule.

### R-2: The model call runs asynchronously, never inline in the user's transaction
- Basis: the platform forbids the inline form.
- Acceptance, positive: submitting a question returns at once with the question in a pending state; the answer
  arrives afterwards. Apex forbids a callout after DML in one transaction and caps a callout at 120 seconds, so the
  call is enqueued rather than made in line. Surface: the conversation. Confirmed by submitting a question.

### R-3: The API credential is held in a Named Credential and never appears in code, metadata or a log
- Basis: implied by R-2.
- Acceptance, positive: searching the deployed metadata and the debug logs for the key returns nothing; rotating the
  credential needs no code change. Surface: the deployed org. Confirmed by search.

### R-4: A re-enqueued or retried job never posts the same answer twice
- Basis: implied by R-2.
- Acceptance, boundary: forcing the job to run twice for one question leaves exactly one answer record on the
  conversation. Surface: the conversation's records. Confirmed by running the job twice.

### R-5: A refusal, a failure and a timeout each give a different visible outcome
- Basis: implied by a salesperson asking a question.
- Acceptance, failure: a 4xx refusal shows that the question could not be accepted; a 5xx failure shows that the
  service is unavailable and the question will be retried; a timeout shows that the answer did not arrive in time
  and offers to ask again. Surface: the conversation. Confirmed with a mock that returns each.

### R-6: A conversation and its turns are stored as records
- Basis: implied by a salesperson asking a question.
- Acceptance, positive: each conversation holds its turns in order, each turn carrying its role, its text, its
  status, its timestamp and the model identifier that produced it. Surface: the stored records. Confirmed by reading
  them.

### R-7: The Apex tests use a mocked callout
- Basis: implied by R-2.
- Acceptance, positive: the test suite passes with no network access, because the HTTP callout is supplied by a mock
  implementation. Surface: the test run. Confirmed by running it offline.

### R-8: The bot's configuration differs per environment
- Basis: implied by the administrator deploying onward.
- Acceptance, positive: the development org, the sandbox and production each resolve their own endpoint and
  credential without a code change, and the deployment to production meets the platform's code-coverage requirement.
  Surface: each org. Confirmed at deployment.
