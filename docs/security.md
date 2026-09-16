# Security boundaries

- Argon2 hashes, expiring JWT access tokens, rotated hashed refresh tokens with HttpOnly/SameSite cookies.
- Access tokens remain in frontend memory. Only non-sensitive comparison IDs use localStorage.
- Ownership checks protect carts, workflows/SSE, orders, returns, support and purchase documents.
- Customer users cannot create procurement requests. Managers cannot approve their own manager-controlled request.
- Short-lived tool-scoped capabilities plus agent permissions and strict Pydantic arguments prevent unrestricted tool use.
- Price, coupon and stock are read from authoritative SQL at checkout; request hashes bind approval to the quote.
- Database unique constraints make duplicate order/payment/refund commits impossible for an operation.
- SQL values use SQLAlchemy bound expressions; no model-authored SQL or shell execution exists.
- Input heuristics reject obvious prompt injection and secret/tool-execution requests. They are not a complete security classifier.
- NGINX security headers and an explicit CORS allowlist are supplied. Keep service ports private and terminate HTTPS before using real accounts.

Local rate limits use the socket client address. Behind the supplied proxy this groups users by proxy address; production must add trusted-proxy configuration and per-principal limits with tests, not trust arbitrary X-Forwarded-For values.

The checkpointer and audit tables can contain user queries and order metadata. Treat them as sensitive operational data: restrict DB access, define retention, encrypt backups and test deletion workflows. LangSmith is opt-in and may receive workflow payloads; deploy a redaction policy before enabling it for real customers. The local build did not enable external tracing.

Production gaps include MFA, self-service credential reset, account recovery, tenant isolation for business organizations, abuse testing, signature verification for payment/carrier webhooks, and audit retention/tamper-evidence. Do not expose demo credentials publicly.


## Release-candidate hardening

Mutating request bodies are capped at 64 KiB, malformed JSON is rejected, browser origins and accepted hosts are checked, and production cookie authentication requires an allowed Origin. Responses disable API caching, add browser security headers and production HSTS, and hide interactive API documentation in production. Missing accounts use a dummy password verification to reduce timing differences. Specialist context prevents agent-profile impersonation.

The production overlay separates PostgreSQL administrator and non-superuser application credentials, requires unique secrets, adds Redis authentication, disables demo seeding and configures a TLS edge. It remains a single-host configuration and requires runtime review. Python and npm advisory scans reported no known vulnerabilities in the supplied snapshots; image scanning and penetration testing remain open.
