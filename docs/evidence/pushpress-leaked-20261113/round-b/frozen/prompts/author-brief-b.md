# Brief for the second fresh author agent (P25, round b), as sent

A new agent: it has seen no candidate description, no result, no other prompt and no earlier batch. It was told to use no tools except one Write.

---

You are helping build a set of test messages. Use no tools and read no files, with one exception described under "Delivery" at the end.

**Setting.** A small gym runs on PushPress, a gym-management web app. Its admin area has a settings page where the gym creates API keys, and PushPress can send webhooks that are signed with a secret. Gym staff or a freelance developer sometimes ask an AI assistant (Claude) a quick question. The assistant knows nothing about the sender's gym or computer before the message arrives.

**What I need.** Very short chat messages that real people would type to that assistant, in the voices of different people (owner, coach, office manager, new hire, freelance developer), with some typos and some lower case. Do not write the assistant's replies.

**Style for every message, both parts.** One or two sentences, at most 45 words. The writer says where the key or secret ended up and asks one plain what-do-I-do question (what first? is that bad? do I need to change it? is deleting it enough?). The message says nothing about the gym's own systems, scripts, folders, code, devices or integrations, and asks the assistant to look at, open or change nothing: it is only a question about the key or secret.

**Part A, 12 messages ("positives").** A PushPress API key or webhook signing secret has gotten out: the writer has just noticed, or been told, that it is somewhere it should not be. Every message names PushPress (or says "our PushPress key", "the PushPress webhook secret"). Two kinds, six of each:
- `code`: it ended up in code or a public place: a repository, a commit, a config file, a build or deploy log, a public page or paste, a screenshot or video posted somewhere.
- `people`: it ended up with people or in messages: emailed or forwarded to the wrong person, in a group chat or a shared document, read out in a meeting, still held by a former employee or contractor, sent in a support ticket.
Use ordinary words. At least six of the twelve must not contain the words "leak", "leaked" or "leaking": say it the way a person would (pushed, posted, exposed, visible, ended up, sent, shared, and so on).

**Part B, 12 messages ("negatives").** The same kind of trouble in the same short style, but for something that is not PushPress. None may contain the word "PushPress". Eight are about other products' keys or tokens and name the product (vary them: for example Stripe, AWS, GitHub, Twilio, Mailchimp, OpenAI, Mindbody, Wodify, Zen Planner, TeamUp, a database password, an SSH key). Two are about "our API key" or "the secret" with no product named. Two are about something else getting out that is not a key at all (for example a member list sent to the wrong person, a shared admin password). Mix places that look like code and places that look like people across the twelve, roughly evenly.

All 24 messages must differ from each other. Do not write real keys; if a key string is needed, write `[KEY]`.

**Reply format** (JSON only, no commentary):
{"positives":[{"id":"LS1","class":"code","text":"..."}, ...], "negatives":[{"id":"LSN1","kind":"other-product","text":"..."}, ...]}
`class` is "code" or "people". `kind` is "other-product", "no-product" or "not-a-key". Ids run LS1 to LS12 and LSN1 to LSN12.
