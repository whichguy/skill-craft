# Games (Salesforce)
Hot-seat chess on a Lightning App Page. Server code follows the org's layers:
selectors for queries, services for logic, controllers return `ServiceResult`,
`Logger` for errors, `TriggerHandler` for triggers. LWC calls Apex through `c/apex`.
