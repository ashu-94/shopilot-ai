# Contributing

Read the [architecture](docs/architecture.md) and [developer guide](docs/DEVELOPMENT.md) before changing behavior. No code license has been selected yet; discuss contribution and reuse terms with the repository owner before submitting substantial third-party code.

## Workflow

1. Open an issue describing the problem, expected behavior and affected journey. Use private reporting for vulnerabilities.
2. Create a focused branch from the default branch. Keep unrelated formatting and dependency upgrades separate.
3. Implement the change with appropriate validation. Preserve user data and existing migrations.
4. Update documentation and the feature matrix when behavior or verification status changes.
5. Open a pull request using the supplied template. Explain the trigger, resulting behavior, checks run and remaining limitations.

## Invariants to preserve

- Prices, stock, ownership, reviewer roles and tool permissions come from trusted application state.
- Never treat model output as authorization for a financial action.
- Preserve immutable approval payloads, stable idempotency and atomic mock transactions.
- Do not double-apply stock or payment effects in event consumers.
- Use explicit migrations; never repair a database by deleting customer or financial records.
- Use integer rupees and cumulative partial-refund allocation.
- Do not commit secrets, databases, model caches, customer logs or access tokens.

## Checks

Run the relevant commands in [TESTING.md](docs/TESTING.md). A docs-only change needs link/schema/example validation, not a full commerce load test. UI changes need a build and appropriate browser/keyboard checks. Financial, permission and concurrency changes need regression tests for their invariants. Explain skipped integration checks honestly.

## Style

Python uses Ruff and mypy; React uses TypeScript and Prettier. Keep domain rules outside prompts and route handlers where practical. Prefer readable names and small boundaries. Avoid introducing infrastructure or dependencies without explaining the operational cost.
