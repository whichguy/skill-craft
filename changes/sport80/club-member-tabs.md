---
bump: patch
---
The club role's view of a member's record is catalogued and was checked on the owner's own record: it lists club-only tabs (Notes, Additional Trackings, REPS Membership, Background Screening Due Payment, Archive Member) and lacks Entries, Addresses, Communication Preferences and the Learning Academy, and its tab list and Memberships and Results totals match the personal role's. `sport80 js` now refuses a member read with a club role unless `--param cid=` names the member, and Archive Member and Add Note stay guided, never run.
