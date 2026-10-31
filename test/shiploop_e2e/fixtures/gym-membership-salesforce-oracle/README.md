# Gym membership Salesforce oracle

This project contains only `SLGymOracleTest`, a verification-only Apex test class. The subject app must already be deployed. The adapter renames the `SLGym` prefix to the case prefix, then runs the renamed `<prefix>OracleTest` with `sf project deploy validate --test-level RunSpecifiedTests`; check-only validation leaves no oracle class or test users in the org.

The class uses 12 independent test methods. It creates random `@example.invalid` users with profiles selected by `PermissionsModifyAllData`, assigns the deployed `<prefix>_Access` permission set, and checks refusals as `AuraHandledException` plus persisted record state. It contains no product implementation or `SeeAllData` access.
