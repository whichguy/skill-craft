| Run | pass | minutes | tokens (M) | implement stages | refused callbacks | send-backs (stage: summary) | failed checks |
|---|---|---|---|---|---|---|---|
| A-shared-expenses-s1 | True | 23.9 | 63.4 | 4 | 6 | implement: S1 proof requires test/service.test.js, but implement forbids writing tests and the test s | - |
| A-shared-expenses-s2 | True | 11.3 | 23.9 | 1 | 1 | - | - |
| A-shared-expenses-s3 | True | 13.4 | 24.2 | 1 | 2 | - | - |
| A-shared-expenses-s4 | True | 14.6 | 37.7 | 2 | 3 | implement: S1 proof runs zero tests on this empty baseline, so it cannot confirm C1-C3; the implement; validate-existing: E1 incorrectly described the current checkout; ShipLoop checks the unchanged item base, wh | - |
| A-shared-expenses-s5 | True | 12.6 | 25.7 | 1 | 2 | - | - |
| A-shared-expenses-s6 | True | 12.2 | 21.5 | 1 | 1 | - | - |
| A-shared-expenses-s7 | True | 14.1 | 31.6 | 1 | 2 | - | - |
| A-shared-expenses-s8 | True | 15.8 | 39.3 | 2 | 5 | - | - |
| A-shared-expenses-s9 | True | 16.4 | 32.9 | 2 | 1 | implement: The proof node --test has no tests: it exits 0 with 0 cases. Test authoring is scheduled a | - |
| A-shared-expenses-s10 | True | 11.4 | 28.1 | 3 | 1 | implement: S1 requires node --test to prove TC_1–TC_4 yet the tests do not exist and implement explic; implement: S1 independent HTTP proof passed, but C1–C3 still require unwritten TC_1–TC_4 at implement | - |
| B-shared-expenses-s1 | True | 23.5 | 70.2 | 4 | 5 | test: TC_1 requires expense creation and balances, assigned to later S2 and S3, so it cannot pas | - |
| B-shared-expenses-s2 | True | 14.2 | 35.9 | 2 | 5 | implement: The plan requires node --test to prove TC_1 through TC_4 during implement, but the impleme | - |
| B-shared-expenses-s3 | True | 11.5 | 21.1 | 1 | 2 | - | - |
| B-shared-expenses-s4 | True | 12.9 | 27.6 | 1 | 3 | system-test: node --test failed with unexpected empty JSON response in TC_3 and TC_4; subsequent runs p | - |
| B-shared-expenses-s5 | True | 17.9 | 42.4 | 2 | 3 | - | - |
| B-shared-expenses-s6 | True | 15.0 | 32.1 | 1 | 2 | - | - |
| B-shared-expenses-s7 | True | 13.9 | 23.0 | 1 | 3 | - | - |
| B-shared-expenses-s8 | True | 18.3 | 40.8 | 3 | 4 | - | - |
| B-shared-expenses-s9 | True | 13.5 | 27.7 | 1 | 4 | - | - |
| B-shared-expenses-s10 | True | 11.7 | 20.9 | 1 | 3 | - | - |

| Arm | runs | passed | runs with a send-back | minutes | tokens (M) | refused callbacks | implement stages | K12 applies yes |
|---|---|---|---|---|---|---|---|---|
| A | 10 | 10 | 4 | 14.6 | 32.8 | 2.40 | 1.8 | 0 |
| B | 10 | 10 | 3 | 15.2 | 34.2 | 3.40 | 1.7 | 10 |
