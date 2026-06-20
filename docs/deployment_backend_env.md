# Backend Deployment Environment

Set these environment variables on the backend host:

```text
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres
AUTOMAP_DB_SCHEMA=automap
ALLOWED_ORIGINS=https://auto-map-cyan.vercel.app
FRONTEND_ORIGIN=https://auto-map-cyan.vercel.app
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```

For local development, `ALLOWED_ORIGINS` can also include:

```text
http://localhost:3010,http://127.0.0.1:3010
```

Never set frontend variables to the Supabase database password or service role key.

## Startup Command

Use the FastAPI app, not the repo root as a frontend app:

```bash
uvicorn app.web_ui:app --host 0.0.0.0 --port $PORT
```

## Initialization

Run once after setting `DATABASE_URL`:

```bash
python -m app.main --deployment-init-db
python -m app.main --deployment-seed-catalog
```

The initializer uses safe `CREATE IF NOT EXISTS` operations and refuses `cfs_dev`.

## Publishing Safety

Real ArcGIS publishing remains disabled by default:

```text
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```
