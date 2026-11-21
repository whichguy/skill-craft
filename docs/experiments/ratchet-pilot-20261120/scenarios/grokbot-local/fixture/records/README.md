# The synthetic records

Made-up data for the assistant to work with. Nothing here is real.

- `people.json`: the three people who use the app, each with an `id` and a `name`. There are no passwords.
- `records.json`: the starting records. Every record has an `id`, a `type` (`order` or `account`) and `readers`, the
  ids of the people who may read it. A person may read, and ask to change, only the records that list them as a
  reader. A record a person creates is theirs: its `readers` is that person alone, and an order's `id` is the next
  free `ORD-` number.

These two files are the starting state and stay as they are. The app keeps its own working copy of the records under
its data folder, so a confirmed change survives a restart and the starting state can always be had again by starting
with an empty data folder.
