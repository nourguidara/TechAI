# Error taxonomy and recovery

| Category | Cause and detection | Recovery | Executed test / scenario |
| --- | --- | --- | --- |
| Invalid tool arguments | Pydantic rejects unknown or out-of-range fields | Return MCP ToolError; terminate unsafe request | test_strict, failure-invalid-arguments |
| Missing parameters | Category, quantity or budget missing | Clarification terminal state, no search | stop-missing-quantity |
| Unsupported constraint | other_preferences nonempty | Ask user to restate supported requirements | validate_request code; UI manual mode |
| No matching products | Hard filtering returns empty | no_feasible_offer, no write | availability-brand/ram/storage |
| Budget too low | Decimal total exceeds budget | Exclude offer; independently recheck before commit | availability-budget, test_budget |
| Stale price | scrape age exceeds limit | Exclude offer; refresh independently | availability-stale |
| Stock unknown/out | Explicit stock status not in_stock | Exclude; never infer availability | availability-unknown/soldout |
| Quantity insufficient | Published quantity below request | Exclude | availability-quantity |
| Scraper blocked | HTTP 401/403/429 or CAPTCHA/block status | Stop source, no stealth retry | Live Mytek 403 observation |
| Robots unavailable | Fetch failure or disallow | Fail closed; later explicit refresh | Live initial Spacenet laptop DNS timeout |
| Malformed source data | Missing Product JSON-LD, non-TND currency or invalid price | Log extraction error and skip offer | test_saved_real_metadata, parser validation |
| MCP connection/tool failure | Client connection exception | Up to two bounded retries for recoverable transport failures | failure-recover-* |
| Timeout | 30-second client deadline | Count attempt, bounded retry, terminal error | bounded client invoke; test timeout recovery |
| OpenAI failure | API authentication, quota or transport error | Error terminal state; manual structured mode remains available | Live 429 no credits |
| Database failure | SQLAlchemy/transaction exception | Roll back; no partial order | test_transaction_rollback |
| Price changed | Approved snapshot differs from current offer | Reject; new proposal/approval required | test_price_change, failure-price-change |
| Proposal changed/expired | Hash mismatch or expiration | Reject write | test_tamper, test_expired |
| Duplicate confirmation | Existing proposal/idempotency key | Return original order | test_concurrent_idempotency, API smoke |
| Rejected approval | Trusted proposal marked rejected | Terminal rejection without order | test_rejection, stop-reject |
| Forged approval | Wrong session/hash or graph resume alone | Deny | test_session_and_hash, stop-forged-resume |
| Email connection failure | SMTP connect fails before DATA | Preserve order; durable failed notification; explicit retry | test_email_failure_preserves_order |
| Ambiguous email delivery | Failure after connection/acceptance uncertainty | delivery_unknown or sending; manual reconciliation, no automatic resend | test_email_ambiguous |
| Agent loop/step limit | Counter would exceed configured limit | Stop before next action | test_bound, stop-one-step/five-steps |
| Prompt injection | Instruction-like retailer text or unsafe URL | Treat as data; deterministic permissions/constraints | injection-1 through injection-7 |

Transport failures are retried at most twice. Business validation failures are not retried because repeating them cannot fix approval, freshness or budget. All tool attempts consume the global step budget. Unexpected failures are surfaced without credentials; expected MCP business errors use ToolError rather than exposing stack traces to the caller.
