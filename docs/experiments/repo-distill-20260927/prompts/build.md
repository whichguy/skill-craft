Build the program specified in `SPEC.md` in this directory. The specification
is the whole requirement; there is no other source, and you must not look for
one. Implement the program yourself: general-purpose libraries are fine, but
do not install or wrap an existing package that already is this program.

Delivery contract: after `npm install`, the program starts with
`node <entry> <arguments>`, where `<entry>` is the file named by the `bin`
field of `package.json` (no build step). If the specification defines a
library interface, importing the package (`package.json` `exports`, or
`main`) must give that interface, also without a build step. Test your work as you see fit and
finish when you are confident every behaviour in the specification holds.
