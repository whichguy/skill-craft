### R-3 Existing data and recovery
The requester decided that startup with DUE_TIMES=on fills missing deadlines from each ticket's stored creation time and priority, saves the file before listening, and requires no separate migration command.
Keep existing deadlines and all other state. Test an enabled startup with a legacy file, inspect disk before the first request, then restart with different settings. A missing file is a fresh installation.
