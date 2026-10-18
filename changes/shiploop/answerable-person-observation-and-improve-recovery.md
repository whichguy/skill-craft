---
bump: minor
---
A check only a person can make is asked so it can be answered, and a partial answer no longer stops the run; a review
interrupted by a context reset no longer redoes a pass it already recorded.
- release-verify asks once, as a fill-in list: step 1 says how to reach the consumer entry and what to answer when it is
  missing or hidden, and the report is one yes/no line per case with what to look for. The run's exclusions bind the run,
  not the person. A reply that answers only some cases resumes the stage: the unanswered ones are recorded not-run, as
  open items for handoff quoting the reply, and the stage completes. It asks again only when the reply answers none, or
  when the run's delivery contract still has a required behavior obligation with no passed observation (then only for
  its unanswered lines).
- The resumed packet prints the person's reply and what it settles in the printed text, not only in the packet file.
- prepare names the consumer's account or role, entry route and access prerequisites and checks them read-only (the
  platform guide's probe where it has one); release-check reruns the same probe before the release. An unresolved
  prerequisite stays open in `environment.md` with who can grant it; ShipLoop's guidance creates no grant. The Salesforce
  card gains the probe: the user's profile and permission sets, and tab, app and class visibility for them.
- The Improve packet the recovery command reprints says which review passes improve-pass has already recorded (and a
  review file written but not recorded), tells the model not to redo a recorded pass, and names one next command:
  improve-pass, which prints a recorded pass's runtime done again when that has not run, and otherwise names the next
  step (the next pass's review file, or the stage's complete once the loop has ended).
