# Implemented plan

1. Add a remainder regression that requires five cents split across three equal
   weights to produce `[2, 2, 1]`.
2. Keep proportional floor shares, then add each remaining cent to the earliest
   input indexes.
3. Preserve durable unit coverage for an unequal remainder, unchanged inputs,
   zero totals, and the listed invalid/bool input categories.
4. Verify the unit suite and bounded valid-input, invalid-input, conservation,
   ordering, and input-immutability checks.
