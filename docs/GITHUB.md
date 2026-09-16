# GitHub repository administration

Intended repository: `ashu-94/shopilot-ai`, public. Publishing the repository does not deploy the application.

## Included repository assets

- A concise root README with screenshots, quick start and navigation.
- Architecture, API, onboarding, demo, tests, configuration and operating guides.
- Contribution and security-reporting instructions.
- Bug/feature issue forms and a pull-request template.
- Existing backend, PostgreSQL/Redis, frontend and container CI jobs.

## Owner follow-up

1. Select a code license before inviting open-source reuse; third-party assets keep their separate terms.
2. Enable private vulnerability reporting, then confirm the Security tab presents a private reporting option.
3. After the initial CI run, configure branch protection around the appropriate passing checks and review requirements. Do not require a check name that has never run.
4. Add repository topics such as `agentic-ai`, `ecommerce`, `langgraph`, `fastapi`, `react`, `mcp`, `rag` and `human-in-the-loop`.
5. Keep secrets in the deployment platform or GitHub secrets, never in committed environment files.

## Manual publishing fallback

If remote publishing is unavailable, create an empty public repository with no generated README, license or gitignore, then run from the project root:

```bash
git remote add origin https://github.com/ashu-94/shopilot-ai.git
git push -u origin HEAD:main
```

If `origin` already exists, inspect it before changing anything. Do not force-push or overwrite another repository's history. Use an authenticated Git credential manager or GitHub CLI; never paste tokens into chat or remote URLs.
