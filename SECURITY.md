# Security reporting

This repository is a release candidate for synthetic commerce. It is not approved for real payments or sensitive customer data. See [security boundaries](docs/security.md) and [release gates](docs/RELEASE_READINESS.md).

Do not publish credentials, exploit payloads, customer data or detailed vulnerability reproductions in public issues. If the repository's Security tab offers **Report a vulnerability**, use that private channel. Otherwise ask the maintainer to establish a private reporting channel before sending sensitive details. No response-time SLA or bug bounty is promised.

Include the affected revision, component, impact, prerequisites and a minimal reproduction using synthetic data. Do not test against systems you do not own or have permission to assess.

Only the current default branch is maintained on a best-effort basis. Public demo passwords and the local-demo JWT default are intentionally documented development fixtures, not production credentials. Production startup refuses demo seeding and unsuitable configuration.
