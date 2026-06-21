# AutoMap Frontend Workflow Shell

AutoMap v3.4 provides a polished Next.js + TypeScript workflow shell centered on the simple Map Composer while keeping the FastAPI backend as the API and workflow engine.

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

In production, browser API requests use the same-origin Vercel proxy route
`/api/automap/*`, which forwards to Render using the server-only
`AUTOMAP_API_SERVER_URL` value.

Do not commit `.env.local`.

Cabarrus FutureScape keeps `http://localhost:3000` and `http://127.0.0.1:8000`. AutoMap must not bind to those ports.

## Visible Pages

- `/dashboard`
- `/map-composer`
- `/parcel-workspace`
- `/proximity`
- `/scenarios`
- `/analysis`
- `/reports`
- `/layer-catalog`
- `/data-gaps`
- `/external-sources`
- `/history`
- `/system-status`

The root `/` redirects to `/map-composer`.

Internal routes such as `/map-request`, `/clarify`, `/recipe-review`, `/map-preview`, `/adjustments`, `/approval`, and `/publish-center` redirect to `/map-composer` by default. They are not part of the normal user-facing sidebar.

## Workflow Shell

The frontend presents one local, draft-only normal workflow:

1. Request
2. Preview
3. Adjust
4. Print / Export

The composer can still create recipes, local WebMap JSON, review packets, and report/export files behind the scenes. The normal UI does not show the old 10-step internal workflow, and it does not expose real ArcGIS publishing.

Workflow state is stored in browser localStorage under an AutoMap-specific key. It tracks the prompt, composer response, recipe, preview, adjustments, warnings, missing data, and selected workflow artifacts as needed. Protected markers such as database URLs, passwords, tokens, and ArcGIS credential keys are redacted before storage.

## v2.2 Analysis

v2.2 includes an `/analysis` page for safe bounded local GIS execution and user-guided refinement. The page can plan feasibility, show broad and optimized counts, display the selected query strategy, show chunk and safety-limit metadata, execute supported parcel/flood intersection or attribute-filter requests, and link to local GeoJSON results under `outputs/analysis/`.

For parcel/flood/geography requests, AutoMap uses server-side spatial filtering and ObjectID deduplication before downloading parcel geometry.

When execution is blocked because the optimized candidate count is still above the feature limit, the page shows a Refine Analysis panel. Reviewers can create refinement options, select `summary_only`, inspect batch and filter tradeoffs, and execute a local summary that avoids geometry download.

The Map Preview layer panel can display a derived local analysis result badge when an execution result exists in workflow state. Derived results are not uploaded or published.

## v1.8 Clarification Loop

v1.8 added deterministic GIS review questions. In the normal v3.4 UI, those clarification capabilities are surfaced through Map Composer rather than a separate visible `/clarify` page. The underlying components still support single choice, multi choice, text, number, distance, year, and date-range question types.

The original recipe is preserved for comparison. The refined recipe records the local clarification session id, questions, answers, applied refinements, remaining questions, unresolved blockers, and a changes summary.

## v1.9 Learning

v1.9 added approved-pattern learning. It remains a local deterministic capability; it is not exposed as a normal sidebar page in the simplified composer UI.

Learned suggestions remain reviewable. The frontend does not expose real publishing or ArcGIS login.

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
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `GET /api/patterns`
- `GET /api/patterns/{pattern_key}`
- `POST /api/patterns/learn-from-approved`
- `POST /api/feedback/recipe`
- `GET /api/clarification-defaults`
- `GET /api/clarification`
- `POST /api/clarification/start`
- `GET /api/clarification/{session_id}`
- `POST /api/clarification/{session_id}/answer`
- `POST /api/clarification/{session_id}/refine`
- `POST /api/clarification/{session_id}/learn`
- `POST /api/analysis/plan`
- `POST /api/analysis/execute`
- `GET /api/analysis/runs`
- `GET /api/analysis/runs/{analysis_run_id}`
- `GET /api/preview-config/{packet_id}`
- `POST /api/recipe`
- `POST /api/review-packet`
- `POST /api/webmap-draft`
- `POST /api/adjustment-template`
- `POST /api/apply-adjustments`
- `POST /api/approval-template`
- `POST /api/apply-approval`
- `POST /api/generate-report`
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

AutoMap still does not bulk-ingest full geometries, does not download full feature datasets, and does not use an external LLM API.
