# AutoMap Frontend App Shell

AutoMap v1.4 adds a Next.js + TypeScript frontend while keeping the FastAPI backend as the API and workflow engine.

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
