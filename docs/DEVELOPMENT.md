# Developer onboarding

## Start with a running application

Follow the root [quick start](../README.md#quick-start). Keep the API on 8000 and frontend on 5173. The frontend proxies `/api` to the API; browser access tokens remain in memory and refresh cookies restore sessions.

For UI development, run `npm run dev` inside `frontend/`. The preview command serves a production build and therefore needs another build after source edits. On the Windows build host, preview also avoids a development loader permission issue.

## Read the code in this order

1. [main.py](../backend/main.py) and [schemas.py](../backend/schemas.py): request boundaries and workflow creation.
2. [workflows.py](../backend/workflows.py): supervisor, specialist graph, review and persistence.
3. [tools.py](../backend/tools.py) and [MCP server](../mcp_servers/server.py): permissions and validated capabilities.
4. [commerce.py](../backend/commerce.py): financial and quantity invariants.
5. [events.py](../backend/events.py): durable outbox and deduplicated consumer effects.
6. [rag.py](../backend/rag.py), [semantic.py](../backend/semantic.py), [recommendations.py](../backend/recommendations.py): grounding and selection.
7. [frontend/src/main.tsx](../frontend/src/main.tsx), [layout.tsx](../frontend/src/layout.tsx) and [pages](../frontend/src/pages): routing and user journeys.

## Common changes

| Change | Touch | Validate |
|---|---|---|
| Product presentation | Shared components, pages, styles | Build, responsive and keyboard behavior |
| Domain rule | Commerce/service code, schemas | Invariant, replay and permission tests |
| Specialist behavior | Graph registration and specialist handler | Output contract, tool scope and failure path |
| Schema | Models and new Alembic revision | Fresh upgrade and populated-data compatibility |
| Event handling | Envelope validation and consumer transaction | Duplicate and out-of-order behavior |
| Retrieval | Semantic/RAG pipeline and evaluation cases | Source filtering and relevance regression |

## Working with data

The local `data/` directory holds databases, checkpoints and model caches. It is ignored by Git. Do not delete it to fix connectivity. Seeding is idempotent, so changing seed definitions does not automatically overwrite existing records. Test servers create disposable databases; never point test URLs at production stores.

Use Alembic for schema evolution. Back up populated stores before migrations. Changes to item-level returns may not be representable in older schemas; read migration downgrade guards and the [runbook](RUNBOOK.md).

## Configuration and troubleshooting

- Connection refused: verify the API health endpoint and frontend port, then use the local launcher.
- UI changes absent: rebuild Vite preview and refresh the page.
- Learned model startup is slow: first use downloads weights; preserve the model cache.
- An approval is paused: use its authorized owner/independent reviewer; do not edit stored payloads.
- Docker permission errors: run the stack verification from a session with Docker Engine access.

See [configuration](CONFIGURATION.md), [testing](TESTING.md) and [operations](RUNBOOK.md).
