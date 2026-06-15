# Local Web UI

AutoMap v0.8 adds a local FastAPI + Jinja2 web interface for running the draft map workflow without relying only on terminal commands.

The UI is local only and binds to localhost by default:

```bash
python -m app.main --serve-ui
```

Then open:

```text
http://127.0.0.1:8000
```

If another local service is already using port `8000`, use a temporary local override:

```bash
python -m app.main --serve-ui --ui-port 8001
```

## What The UI Supports

- Build a map recipe from a plain-English prompt.
- Generate a review packet.
- Generate a WebMap draft JSON.
- Create and edit an adjustment YAML template.
- Apply adjustments to create a separate adjusted packet.
- Validate adjusted packets.
- Run dry-run publishing only.
- Search the layer catalog.
- View data gaps.

## Safety Boundary

Every page includes:

```text
AutoMap drafts are for GIS review only. They are not official maps and are not published unless explicitly approved.
```

The UI does not publish real ArcGIS items. Dry-run publishing writes a receipt and creates no item. Real publishing remains CLI-only and guarded by explicit confirmation.

The UI does not require ArcGIS login, does not use an external LLM API, does not ingest geometries, and does not download full feature datasets.

Generated outputs remain under `outputs/`, which is ignored by Git.

## Main Routes

- `GET /`
- `POST /recipe`
- `POST /review-packet`
- `POST /webmap-draft`
- `POST /adjustment-template`
- `POST /apply-adjustments`
- `POST /publish-dry-run`
- `GET /catalog`
- `GET /data-gaps`
- `GET /health`

## Project Boundary

AutoMap uses its own local database and schema. The CFS database is separate and must not be touched by the local UI.
