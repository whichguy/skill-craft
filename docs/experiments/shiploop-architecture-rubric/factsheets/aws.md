# AWS Serverless Fact Sheet

## 1. Identity and sign-in for end users
- Cognito **user pools** authenticate users and issue JWTs (ID/access/refresh); apps use hosted UI, SDKs, or Amplify. [Cognito user pools JWT docs](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html)
- Server-side verification: API Gateway HTTP API **JWT authorizers** validate signature via the issuer's `jwks_uri`, checking algorithm/issuer/audience; only RSA-based algorithms are supported and the key is cached for a bounded time. [HTTP API JWT authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)
- Alternative: a Lambda authorizer or backend code verifies the Cognito JWT itself (e.g., via `aws-jwt-verify`) against the pool's public keys. [Decode/verify Cognito JWT](https://repost.aws/knowledge-center/decode-verify-cognito-json-token)

## 2. Authorization patterns
- **IAM auth**: caller signs requests with SigV4; API Gateway resource policies plus IAM policy must both allow access. [Resource policy authorization flow](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-authorization-flow.html)
- **Cognito authorizer**: built into REST/HTTP APIs; **not available for WebSocket APIs**, which require a Lambda REQUEST authorizer instead. [WebSocket + Cognito sample](https://github.com/aws-samples/websocket-api-cognito-auth-sample/blob/main/README_en.md)
- **Lambda authorizers**: TOKEN (single header) or REQUEST (headers/query/context) types; return an IAM policy, cacheable. [Lambda authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- **Cognito identity pools** exchange an authenticated (or guest) identity for temporary IAM credentials via `AssumeRoleWithWebIdentity`, for direct, fine-grained per-user AWS API access (e.g., S3/DynamoDB). [Identity pools guide](https://tutorialsdojo.com/amazon-cognito-user-pools-vs-identity-pools/)

## 3. State and storage, consistency, transactions
- DynamoDB reads default to **eventually consistent**; set `ConsistentRead=true` on GetItem/Query/Scan for strongly consistent reads (higher RCU cost). [Read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)
- `TransactWriteItems`/`TransactGetItems` give ACID guarantees but **only within one AWS Region** — not across Global Tables replicas; each item consumes double capacity. [Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- S3 delivers **strong read-after-write consistency** for all GET/PUT/LIST and metadata/ACL/tag operations, automatically, no cost. [S3 consistency](https://aws.amazon.com/s3/consistency/)

## 4. Concurrency control
- DynamoDB **optimistic locking**: condition expressions on a version attribute; mismatch raises `ConditionalCheckFailedException`, evaluated atomically with the write. [Optimistic locking](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_OptimisticLocking.html)
- Lambda **reserved concurrency** caps/guarantees per-function concurrent executions from the account pool; **provisioned concurrency** pre-initializes environments (billed separately). [Lambda concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html), [Provisioned concurrency](https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html)

## 5. Connectivity channels
- **Request/response**: API Gateway REST/HTTP APIs + Lambda proxy integration — supported. [API Gateway dev guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- **Polling**: client-side polling against REST/HTTP endpoints — supported, no special AWS primitive.
- **Streaming/SSE**: Lambda **function URLs** with `RESPONSE_STREAM` invoke mode stream chunked payloads (good for SSE); native runtime support is Node.js, others need a runtime shim (e.g., Lambda Web Adapter); **not supported inside a VPC** via function URL (use `InvokeWithResponseStream` API instead). [Response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html), [Streaming + function URLs](https://docs.aws.amazon.com/lambda/latest/dg/config-rs-invoke-furls.html)
- **WebSockets**: API Gateway WebSocket APIs (connect/disconnect/route + `@connections` POST) — supported, with the authorizer caveat in §2.
- **AppSync subscriptions**: real-time GraphQL over a managed WebSocket connection, triggered by mutations; AppSync only supports pure WebSockets (not SSE). [AppSync real-time data](https://docs.aws.amazon.com/appsync/latest/devguide/aws-appsync-real-time-data.html)
- **Platform push** (APNs/FCM): not covered by the services above; typically via SNS mobile push — unverified beyond scope here.

## 6. Caching options and staleness
- **DAX**: write-through cache in front of DynamoDB; item/query cache is **eventually consistent only** — strongly consistent reads and `TransactGetItems` bypass the cache and go straight to DynamoDB (uncached). [DAX consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)
- **ElastiCache** (Redis/Valkey/Memcached): app-managed cache-aside or write-through, staleness controlled entirely by your TTL/invalidation logic — unverified specifics beyond general product docs.

## 7. Secrets custody
- **Secrets Manager**: built for credentials, supports automatic/managed rotation, versioning with staging labels, cross-region replication; charged per secret + API calls. [Secrets Manager vs Parameter Store](https://tutorialsdojo.com/aws-secrets-manager-vs-systems-manager-parameter-store/)
- **SSM Parameter Store**: general config + SecureString parameters (KMS-encrypted); Standard tier free, no built-in rotation workflow, no cross-region replication.

## 8. Scheduling, queues, background work
- **EventBridge Scheduler**: configurable retry policy plus an SQS **dead-letter queue** for schedules that exhaust retries. [Scheduler DLQ](https://docs.aws.amazon.com/scheduler/latest/UserGuide/configuring-schedule-dlq.html)
- **SQS→Lambda**: at-least-once delivery — **handlers must be idempotent**; failed batches become visible again after the visibility timeout; configure a **redrive policy** DLQ and use `ReportBatchItemFailures` for partial-batch retries. [SQS+Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- **Step Functions**: `Retry` (with backoff/jitter, matched top-to-bottom by `ErrorEquals`) and `Catch` fields on Task/Parallel/Map states; uncaught errors fail the execution. [Error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)

## 9. Limits to check
- [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html) · [API Gateway quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html) · [DynamoDB quotas](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotasRevised.html) · [EventBridge Scheduler DLQ config](https://docs.aws.amazon.com/scheduler/latest/UserGuide/configuring-schedule-dlq.html)

## 10. Deployment and verification surface
- `sam local start-api`/`invoke` emulate the Lambda runtime and API Gateway routing locally, but **do not emulate other AWS services** (DynamoDB, S3, etc.) — calls to them hit real AWS or fail; also can't emulate Lambda `/mnt` filesystem mounts. [SAM local start-api](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-start-api.html) — passing local tests proves handler logic, not IAM permissions, cold-start behavior, or integration wiring.

## 11. Common false claims and corrections
- ❌ "S3 is only eventually consistent." ✅ Strong read-after-write consistency since Dec 2020, automatic. [S3 consistency](https://aws.amazon.com/s3/consistency/)
- ❌ "DynamoDB transactions are ACID across Global Tables regions." ✅ ACID only within the region where the write API was called. [Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)
- ❌ "WebSocket APIs support a built-in Cognito user-pool authorizer like REST/HTTP APIs." ✅ Not supported; must use a Lambda authorizer. [WebSocket sample](https://github.com/aws-samples/websocket-api-cognito-auth-sample/blob/main/README_en.md)
- ❌ "DAX makes strongly consistent DynamoDB reads eventually consistent." ✅ DAX passes strong reads/`TransactGetItems` straight through, uncached. [DAX consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)
- ❌ "SAM local fully emulates AWS for integration testing." ✅ It emulates only Lambda/API Gateway routing, not downstream services. [SAM local start-api](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-start-api.html)
- ❌ "Lambda function URL response streaming works the same inside a VPC." ✅ Not supported in VPC via function URL; use the SDK `InvokeWithResponseStream` API instead. [Response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)

**As of:** 2026-09-26, checked against current AWS docs pages linked above (Lambda Developer Guide, API Gateway Developer Guide, DynamoDB Developer Guide, AppSync Developer Guide, Step Functions Developer Guide, EventBridge Scheduler User Guide, SAM Developer Guide, Cognito Developer Guide). No specific service API/console versions apply; AWS docs are continuously updated and unversioned.
