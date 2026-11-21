# The stand-in provider

`provider/standin.js` stands in for a language model. It runs offline, and the same input always gives the same
output, so the app can be used and checked without any outside service. Every assistant reply in the app comes from it.
Use it as it is: do not edit it, copy it or replace it.

```js
const { respond, runStep, check, ProviderError } = require('./provider/standin');
```

## The token

The stand-in needs a provider token: the text `sk-local-` followed by at least twelve letters or digits. `check(token)`
says whether a token is acceptable. A call with a missing or wrong token throws `ProviderError` ("unauthorized"). The
token is a secret: it belongs to whoever runs the app, and no person using the app should ever be shown it.

## A reply: `respond(input)`

```js
const output = await respond({
  token,                                  // the provider token
  bot: { name, instructions },            // the bot that is answering; instructions is '' when it has none
  person: { id, name },                   // who is asking
  memory: ['likes tea'],                  // what this bot remembers about this person
  messages: [                             // this conversation so far, oldest first, ending with the new message
    { from: 'person', text: 'hello' },
    { from: 'bot', text: '...' },
    { from: 'person', text: 'what did I ask first' },
  ],
  records: [/* only the records this person may read */],
  attempt: 1,                             // 1 for the first try of this message, 2 for a retry of it, and so on
});
```

It answers only from what it is given. A bot's memory, an earlier turn or a record that is not in the input does not
exist for it. `output.text` is always the reply to show. The other fields ask the app to do something:

| Field | Meaning | What the app does |
|---|---|---|
| `remember: [fact]` | The person asked the bot to remember something | Add each fact to what this bot remembers about this person |
| `forget: [fact]` | The person asked the bot to forget something | Remove that fact from what this bot remembers about this person |
| `clarify: true` | The reply is a question the bot needs answered | Show it; the person's next message answers it, so it must arrive with the conversation so far |
| `proposal: { summary, changes }` | The person asked for records to be created or changed | Show the exact changes and write nothing until the person confirms |
| `task: { title, steps, controls }` | The person asked for longer work | Do the steps in the background, one `runStep` call each, in order |
| `steer: { add }` | The person added to the work that is running | Add that step to the end of their running task in this conversation |

A change in `proposal.changes` is either `{ record, field, from, to }` (set one field of an existing record) or
`{ create: { type, ... } }` (a new record).

## What it understands

The first rule that fits the person's last message is used. Capitals do not matter.

| The person says | The reply |
|---|---|
| `remember that <fact>` | "I'll remember that `<fact>`." with `remember` |
| `forget <fact>` or `forget that <fact>` | "I've forgotten ..." with `forget` |
| `what do you remember` | "I remember: a; b." from `memory`, or "I don't remember anything about you yet." |
| `who are you` | "I am `<bot name>`." and the bot's instructions, or "I have no special instructions." |
| `what did I ask first` | "You first asked: ..." from `messages` |
| `how many orders can you see` (or accounts, ...) | "I can see N order record(s)." counted from `records` |
| `what is the <field> of <ID>` | "The `<field>` of `<ID>` is `<value>`.", or "I can't see a record called `<ID>`." |
| `set the <field> of <ID> to <value>` | a `proposal` with one change, or "I can't see a record called `<ID>`." |
| `update <ID>` | the question "Which field of `<ID>` should I change, and to what value?" with `clarify` |
| `the <field> to <value>`, right after that question | the same `proposal` as `set the <field> of <ID> to <value>` |
| `create an order for <customer> totalling <number>` | a `proposal` that creates one open order |
| `long task: <title>` or `research: <title>` | "I'll work on ..." with a `task` of three steps |
| `add step: <text>` | "I'll add ..." with `steer` |
| anything else | `You said: "<text>". (<bot name> has N message(s) from you in this conversation.)` |

Three markers in a message change how the stand-in behaves, so that slow and failing replies can be tried out:

- `[slow]` makes the reply take `STANDIN_SLOW_MS` milliseconds (1500 unless the environment sets it).
- `[fail once]` makes the first attempt throw `ProviderError`; an attempt of 2 or more succeeds.
- In a long task's title, `[long]` gives the task eight steps, and `[fail step 2]` makes its second step fail on the
  first attempt.

## A step of a long task: `runStep(input)`

```js
const { text } = await runStep({ token, task, index: 0, attempt: 1 });   // "Done: <the step>"
```

`task` is the object `respond` returned, `index` counts from 0, and `attempt` is 1 for the first try of that step. Each
step takes `STANDIN_STEP_MS` milliseconds (500 unless the environment sets it). A step that fails throws
`ProviderError`.
