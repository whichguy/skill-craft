---
bump: patch
---
The lint gate now blocks only an item's last implement step. Earlier steps
report their findings without auto-fix, since a later step may resolve them
(for example, an import the next step uses).

Once a loop's receipt exists, the loop packet says not to run Start again and
to continue from the receipt's `next_argv`.

Paused, halted and blocked packets longer than 16,000 characters now print a
pointer to the full packet file and what fits, so they stay under hosts'
shell-output limits.
