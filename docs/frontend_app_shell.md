# AutoMap Frontend Workflow Shell

AutoMap v2.0 provides a polished Next.js + TypeScript workflow shell with interactive clarification, deterministic feedback learning, and safe bounded analysis while keeping the FastAPI backend as the API and workflow engine.

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
- `/clarify`
- `/recipe-review`
- `/map-preview`
- `/analysis`
- `/adjustments`
- `/approval`
- `/publish-center`
- `/learning`
- `/reports`
- `/layer-catalog`
- `/data-gaps`
- `/history`
- `/system-status`

The root `/` redirects to `/dashboard`.

## Workflow Shell

The frontend presents a local, draft-only workflow:

1. Dashboard quick prompt and system snapshot
2. Map request recipe generation
3. Interactive clarification when the request needs distance, time range, flood scope, zoning, or missing-data decisions
4. Recipe review with selected layers, filters, operations, warnings, and gaps
5. Local WebMap preview through the backend preview route
6. Safe bounded analysis with local GeoJSON outputs
7. Human YAML adjustments that create separate adjusted packets
8. Reviewer approval that records local readiness only
9. Dry-run publish and dry-run portal smoke-test receipts
10. Approved-pattern learning from local approved packets
11. Local report/export packages for GIS review

The shell uses compact cards, status chips, scan-friendly tables, grouped warning panels, layer review panels, and explicit draft-only labels. It does not expose real ArcGIS publishing.

Workflow state is stored in browser localStorage under an AutoMap-specific key. It tracks the prompt, initial recipe, refined recipe, clarification session, clarification answers, WebMap draft, review packet, analysis plan, analysis run, adjustment template, adjusted packet, approval template, approved packet, dry-run receipt, smoke-test receipt, active step, warnings, missing data, and selected packet ids. Protected markers such as database URLs, passwords, tokens, and ArcGIS credential keys are redacted before storage.

## v2.0 Analysis

v2.0 adds an `/analysis` page for safe bounded local GIS execution. The page can plan feasibility, show count estimates and blockers, execute supported parcel/flood intersection or attribute-filter requests, and link to local GeoJSON results under `outputs/analysis/`.

The Map Preview layer panel can display a derived local analysis result badge when an execution result exists in workflow state. Derived results are not uploaded or published.

## v1.8 Clarification Loop

v1.8 adds a `/clarify` page for answering AutoMap's deterministic GIS review questions. The page supports single choice, multi choice, text, number, distance, year, and date-range question types. Answers are saved to the local backend, converted into an explicit refinement context, and used to regenerate the request intelligence, analysis plan, selected layers, filter plan, warnings, and map recipe.

The original recipe is preserved for comparison. The refined recipe records the local clarification session id, questions, answers, applied refinements, remaining questions, unresolved blockers, and a changes summary.

## v1.9 Learning

v1.9 adds a `/learning` page for the approved pattern library. The page lists approved patterns, common clarification defaults, learned layer preferences, learned assumptions, recent feedback rows, and a local action to learn from an approved packet.

Learned suggestions are shown on Map Request, Recipe Review, and Clarify Request. They remain reviewable. The frontend does not expose real publishing or ArcGIS login.

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
