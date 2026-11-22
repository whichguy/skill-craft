### R-3. Backfill and rollout gate

The requester decided that when DUE_TIMES=on, startup automatically fills every missing deadline from the ticket's created instant and stored priority, saves the file, and only then serves requests.
Existing deadlines stay unchanged, and missing deadlines never cause startup to refuse a valid legacy file. With DUE_TIMES unset or anything other than on, preserve previous public responses including ignored overdue queries. Verify a valid legacy file starts while disabled, and enabled startup saves its backfill before the first request. Verify repeated startup preserves dates.
