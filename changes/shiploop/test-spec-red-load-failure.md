---
bump: patch
---
Test-spec now says what ShipLoop's base run already accepts: a case may be RED on the item's base because the code the item
adds does not load yet (a new module on an empty base). Its RED placeholder no longer reads "not because a file is", which led
test-spec to send plans back for a new module's honest load failure; a guard that only checks a file is still not RED.
