# AutoMap Frontend Workflow Shell

AutoMap v1.6 provides a polished Next.js + TypeScript workflow shell while keeping the FastAPI backend as the API and workflow engine.

## URLs

Backend API and existing FastAPI/Jinja UI:

```text
http://127.0.0.1:8010
```

Next.js frontend:

```text
http://localhost:3010
```

## Start Backend

```bash
python -m app.main --serve-ui --ui-port 8010
```

The backend exposes JSON routes under `/api/*`, keeps the existing Jinja pages, and still runs all workflow logic locally.

## Start Frontend

```bash
cd frontend
npm install
npm run dev
```

`frontend/.env.example` points the frontend at the backend:

```text
NEXT_PUBLIC_AUTOMAP_API_BASE_URL=http://127.0.0.1:8010
```

Do not commit `.env.local`.

Cabarrus FutureScape keeps `http://localhost:3000` and `http://127.0.0.1:8000`. AutoMap must not bind to those ports.

## Pages

- `/dashboard`
- `/map-request`
- `/recipe-review`
- `/map-preview`
- `/adjustments`
- `/approval`
- `/publish-center`
- `/layer-catalog`
- `/data-gaps`
- `/history`
- `/system-status`

The root `/` redirects to `/dashboard`.

## Workflow Shell

The frontend presents a local, draft-only workflow:

1. Dashboard quick prompt and system snapshot
2. Map request recipe generation
3. Recipe review with selected layers, filters, operations, warnings, and gaps
4. Local WebMap preview through the backend preview route
5. Human YAML adjustments that create separate adjusted packets
6. Reviewer approval that records local readiness only
7. Dry-run publish and dry-run portal smoke-test receipts

The shell uses compact cards, status chips, scan-friendly tables, grouped warning panels, layer review panels, and explicit draft-only labels. It does not expose real ArcGIS publishing.

Workflow state is stored in browser localStorage under an AutoMap-specific key. It tracks the prompt, recipe, WebMap draft, review packet, adjustment template, adjusted packet, approval template, approved packet, dry-run receipt, smoke-test receipt, active step, warnings, missing data, and selected packet ids. Protected markers such as database URLs, passwords, tokens, and ArcGIS credential keys are redacted before storage.

## v1.6 UX Polish

v1.6 improves the product shell with:

- a stronger dashboard hero and system health summary
- quick prompt entry and demo scenario cards
- a safety status card for dry-run-only publishing and AutoMap/CFS port separation
- clearer workflow stepper blockers and next-step guidance
- better empty, loading, backend-offline, and timeout states
- a data-gap page that explains missing approved sources instead of treating them as failures
- reusable layer and warning panels for map preview review

The current frontend map preview uses the existing local backend preview route inside a draft-only shell. It reads preview config from `/api/preview-config/{packet_id}`, displays operational layer metadata, honors recorded visibility, opacity, and definition expression metadata in the review panel, and links to REST layer endpoints for human inspection. No ArcGIS login or publish operation is required.

## API Coverage

The frontend uses JSON-only backend API routes:

- `GET /api/status`
- `GET /api/catalog/search?q=flood`
- `GET /api/data-gaps`
- `GET /api/history`
- `GET /api/packets`
- `GET /api/preview-config/{packet_id}`
- `POST /api/recipe`
- `POST /api/review-packet`
- `POST /api/webmap-draft`
- `POST /api/adjustment-template`
- `POST /api/apply-adjustments`
- `POST /api/approval-template`
- `POST /api/apply-approval`
- `POST /api/publish-dry-run`
- `POST /api/portal-smoke-test-dry-run`

API responses are sanitized to avoid secrets, database URLs, ArcGIS credentials, and protected external-project references.

## Publishing Boundary

The frontend only exposes dry-run publish and dry-run portal smoke-test actions. It does not expose a real publish button, does not require ArcGIS login, does not create public items, and does not share to the organization.

Real private Portal publishing remains CLI-only behind the existing safety gates.

## Verification

```bash
python -m pytest
python -m app.main --check-db
python -m app.main --system-status

cd frontend
npm run typecheck
npm run build
```

AutoMap still does not ingest full geometries, does not download full feature datasets, and does not use an external LLM API.
