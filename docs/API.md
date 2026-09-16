# API guide

Development base URL: `http://127.0.0.1:8000/api`. The frontend uses same-origin `/api` through its proxy. Interactive development docs are at `/docs`; production disables them. Route source: [main.py](../backend/main.py). Payload source: [schemas.py](../backend/schemas.py).

## Authentication

`POST /auth/login` accepts `email` and `password`, returns an access token and user, and sets a rotating HttpOnly refresh cookie. Send `Authorization: Bearer <access_token>` for authenticated API calls. `POST /auth/refresh` rotates the refresh session; `POST /auth/logout` ends it. Browser cookie authentication in production requires an allowed Origin. Do not put tokens into URLs or persistent frontend storage.

## Core endpoints

| Method | Relative route | Purpose |
|---|---|---|
| GET | `/products`, `/products/{product_id}` | Catalog facts |
| GET / PUT | `/cart` | Read/replace the authenticated user's cart |
| POST | `/missions` | Queue shopping, procurement or support workflow |
| POST | `/checkout` | Snapshot cart and queue reviewed purchase |
| GET | `/executions`, `/executions/{execution_id}` | Owned execution status and result |
| GET | `/executions/{execution_id}/events` | Authenticated SSE progress |
| GET | `/executions/{execution_id}/agents` | Specialist execution records |
| POST | `/executions/{execution_id}/retry` | Retry eligible failed work |
| GET | `/approvals` | Reviews visible to the principal |
| POST | `/approvals/{approval_id}/decision` | Approve, reject or request information |
| GET | `/orders`, `/orders/{order_id}` | Owned orders |
| GET | `/orders/{order_id}/purchase-order` | Procurement JSON document |
| POST | `/orders/{order_id}/cancel` | Queue reviewed cancellation |
| POST | `/returns` | Queue selected-item refund/replacement |
| GET | `/notifications` | In-app notifications |
| POST | `/notifications/{notification_id}/read` | Mark an owned notification read |
| GET | `/operations`, `/admin` | Role-restricted operational views |
| GET | `/admin/recovery` | Administrator recovery inventory |
| POST | `/admin/outbox/{event_id}/replay` | Audited unpublished event replay |
| POST | `/admin/workflows/{execution_id}/recover` | Recover eligible failed/expired workflow |
| POST | `/admin/dead-letters/{letter_id}/replay` | Revalidate and replay stored envelope |

Health endpoints `/health/live`, `/health/ready` and metrics `/metrics` are outside the `/api` prefix. Do not expose operational endpoints unnecessarily.

## Request examples

Shopping mission:

```http
POST /api/missions
Authorization: Bearer <access_token>
Content-Type: application/json
Idempotency-Key: mission-example-001

{"query":"Build a home office under 150000 rupees","mode":"shopping","budget":150000}
```

Replace a cart:

```json
{"items":[{"product_id":"product-001","quantity":1}]}
```

Submit checkout with a fresh `Idempotency-Key`:

```json
{"address":"42 Demo Avenue, Bengaluru 560001","simulate_failure":false}
```

Submit one item for return (use an actual owned order ID):

```json
{"order_id":"<order_id>","items":[{"product_id":"product-001","quantity":1}],"reason":"The product arrived damaged.","resolution":"refund"}
```

Decide an approval:

```json
{"decision":"approve","feedback":"Reviewed exact products, quantities and amount."}
```

These are request payload examples, not fabricated successful responses. Queue endpoints return HTTP 202 and an execution object with an `id`. Poll that execution or consume its events. Financial execution waits for the authorized reviewer. Request-information leaves the workflow paused.

## Idempotency and errors

Checkout and financial workflow submissions require an `Idempotency-Key`. Use the same key for transport retries of the same input; changed input with a reused key is rejected. A new key is a new request and does not replace an earlier approval.

Domain failures use `{"error":{"code":"...","message":"..."}}`. Schema failures use FastAPI's `detail` validation list. Typical statuses: 401 authentication, 403 authorization, 404 missing/inaccessible resource, 409 conflict or stale decision, 422 invalid input, 413 oversized body, 429 rate limit. Code and OpenAPI remain authoritative; response schemas and pagination are not promised as a versioned external SDK contract.
