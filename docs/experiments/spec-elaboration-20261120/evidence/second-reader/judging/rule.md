# Rules

## The class of an item

Give each item exactly one class. Take the first that applies, in this order.

1. `unfounded`: the specification does not say this, and neither `told` nor the request does. The item reports as
   decided something the work did not record.
2. `told`: `told` already tells this decision: the same point, whichever words it uses. An item that adds a different
   consequence of a point `told` names is not `told`.
3. `settled`: not a choice of this work. The request states it, or the program already behaved so before the work and
   the request does not ask for that to change.
4. `unseen`: a choice that a person who uses or runs the program would not notice: internal structure, names, file
   layout, how it is tested, how the work is organised.
5. `new`: none of the above. A choice the work made that the request does not settle, that a person who uses or runs
   the program would notice (what they see, a step they must take, something refused), and that `told` does not tell.

## Three questions about each file

They are about `told` and `specification`, not about the items.

- `told_way_back`: does `told` tell the requester what going back to the earlier release loses or requires (for
  example that the earlier release drops the due times when it next saves, or that an operator must keep a copy)?
- `spec_refuses`: does the specification say that the service refuses to start, or stops before serving, when it is
  started with due times switched on while some ticket in the data file has no due time?
- `told_refusal`: does `told` tell the requester that refusal?

For a request that has nothing to do with due times, all three are false.

## Two described decisions

Give the place of the first item about each, or 0 when no item is about it.

- `way_back`: what going back to the earlier release, 1.4.0, loses or requires. The earlier release can read the data
  file, but its next save drops the due times, so they are lost unless an operator kept a copy or restores one. An
  item is about it when it names this loss, the copy or the restoring, however worded. An item that says only that the
  earlier release can still start on the file and show every ticket is not.
- `refusal`: what the service does when it is started with due times switched on while some ticket in the data file
  has no due time: it refuses to start, or stops before serving. An item is about it when it names that refusal,
  however worded. An item that says only who fills in the due times, or that a command must be run first, is not.
