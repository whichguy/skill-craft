| Run | pass | minutes | tokens (M) | refused callbacks | send-backs | ledger categories | K12 | intake questions | intake s / tool calls |
|---|---|---|---|---|---|---|---|---|---|
| A-hello-s1 | True | 9.2 | 18.2 | 0 | - | 11 | n/a | 0 | 22.9 / 5 |
| A-hello-s2 | True | 14.6 | 24.0 | 1 | - | 11 | n/a | 3 | 21.0 / 5 |
| A-hello-s3 | True | 9.5 | 16.8 | 0 | - | 11 | n/a | 2 | 24.8 / 6 |
| A-hello-s4 | True | 9.9 | 16.8 | 0 | - | 11 | n/a | 1 | 26.8 / 6 |
| A-hello-s5 | True | 8.5 | 17.2 | 0 | - | 11 | n/a | 2 | 19.3 / 5 |
| A-hello-s6 | True | 9.9 | 17.6 | 1 | - | 11 | n/a | 6 | 21.8 / 6 |
| A-ticket-assignment-s1 | True | 22.0 | 60.9 | 2 | - | 11 | n/a | 11 | 28.2 / 6 |
| A-ticket-assignment-s2 | True | 29.0 | 66.7 | 2 | - | 11 | n/a | 10 | 24.6 / 6 |
| A-user-listing-s1 | True | 10.8 | 15.5 | 1 | - | 11 | n/a | 2 | 31.3 / 4 |
| A-user-listing-s2 | True | 13.3 | 21.1 | 0 | - | 11 | n/a | 6 | 32.4 / 7 |
| B-hello-s1 | True | 11.1 | 19.2 | 0 | test-spec | 12 | yes | 3 | 24.1 / 5 |
| B-hello-s2 | True | 13.1 | 19.8 | 2 | test-spec | 12 | no | 0 | 18.6 / 3 |
| B-hello-s3 | True | 12.4 | 25.4 | 0 | - | 12 | no | 1 | 30.9 / 6 |
| B-hello-s4 | True | 10.8 | 17.1 | 0 | - | 12 | no | 3 | 28.0 / 6 |
| B-hello-s5 | True | 10.4 | 20.3 | 2 | test-spec | 12 | yes | 1 | 22.4 / 5 |
| B-hello-s6 | True | 9.6 | 15.4 | 0 | - | 12 | no | 4 | 25.7 / 5 |
| B-ticket-assignment-s1 | True | 17.1 | 26.1 | 2 | implement | 12 | yes | 12 | 28.7 / 5 |
| B-user-listing-s1 | True | 11.1 | 17.9 | 1 | - | 12 | yes | 2 | 27.5 / 7 |
| B-user-listing-s2 | True | 16.2 | 25.9 | 2 | implement | 12 | yes | 5 | 27.1 / 6 |

Round 1, the registered 12-run design (samples 1 and 2; 11 finished):

| Arm | runs | passed | minutes | tokens (M) | refused callbacks | runs with a send-back | intake questions | intake seconds | intake tool calls | K12 applies yes |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 6 | 6 | 16.5 | 34.4 | 1.00 | 0 | 5.3 | 26.7 | 5.5 | 0 |
| B | 5 | 5 | 13.7 | 21.8 | 1.40 | 4 | 4.4 | 25.2 | 5.2 | 4 |

All runs, round 1 and R2 (samples 1 to 6):

| Arm | runs | passed | minutes | tokens (M) | refused callbacks | runs with a send-back | intake questions | intake seconds | intake tool calls | K12 applies yes |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 10 | 13.7 | 27.5 | 0.70 | 0 | 4.3 | 25.3 | 5.6 | 0 |
| B | 9 | 9 | 12.4 | 20.8 | 1.00 | 5 | 3.4 | 25.9 | 5.3 | 5 |
