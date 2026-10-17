# Head table before and after (unit U14, node-fix-bug offline, bare CLI path)

Printed characters / whole characters per stage packet, from SP/eff2/final-verify/fv_heads.py run on this branch before and after the change. A run directory of 83 characters is this machine's default temp path (the script pads only above that); 163 is the live path length. Only the test and verify packets move; every other stage is byte-identical in length.

| run dir | route | stage | before printed / whole | after printed / whole | change printed |
|---|---|---|---|---|---|
| 83 | inline | 08-test | 15,561 / 19,680 | 15,477 / 19,596 | -84 |
| 83 | inline | 10-verify | 15,727 / 19,869 | 15,727 / 19,861 | +0 |
| 83 | ask-agent | 08-test | 15,561 / 21,248 | 15,477 / 21,164 | -84 |
| 83 | ask-agent | 10-verify | 15,926 / 21,636 | 15,926 / 21,628 | +0 |
| 163 | inline | 08-test | 16,682 / 21,200 | 16,598 / 21,116 | -84 |
| 163 | inline | 10-verify | 17,087 / 21,229 | 17,087 / 21,221 | +0 |
| 163 | ask-agent | 08-test | 16,682 / 22,768 | 16,598 / 22,684 | -84 |
| 163 | ask-agent | 10-verify | 17,286 / 22,996 | 17,286 / 22,988 | +0 |

Unchanged in both lengths and both routes (printed and whole): 01-step-plan, 03-test-spec, 05-validate-existing, 06-implement, 09-document, 11-carry-forward. The verify print is unchanged because its changed line, the test rerun list, sits in the packet file below the printed head.
