---
bump: minor
---
A packet no longer prints a text twice. The hand-off block's "Spec and architecture changes since the run began" diff
prints a one-line pointer (file, size, section headings) for a living file that is new since the run baseline, when the same
packet quotes that file whole: such a diff is the whole file. A followed `R-<n>` or `AD-<n>` entry whose exact text is in a
file the packet quotes whole prints as an ID in one line (retired and superseded marks kept); an entry of a file the packet
does not quote still prints its text, and so does any diff that is not exactly the quoted file.
- The block's heading no longer says "the uncut diff"; it reads "nothing cut that is not printed in this packet", which stays
  true when a pointer stands in for text that is printed above it.
- On a long-knowledge fixture (a 20 KB spec, an architecture, an environment file) the quoted-files-and-hand-offs block of the
  `plan` packet falls from 54,450 to 28,734 characters, `test-strategy` from 48,287 to 26,044, `product-acceptance` from
  51,105 to 28,862 and `test-spec` from 37,840 to 28,532. In the live Salesforce chess run 20.7 KB of the plan packet's
  22.1 KB diff was the spec quoted just above it.
