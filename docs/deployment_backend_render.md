# Deploy Backend on Render

AutoMap's backend is the FastAPI app in `app.web_ui:app`.

## Render Service Settings

Create a Render Web Service or Blueprint from:

```text
Repo: https://github.com/khoi9034/AutoMap.git
Branch: main
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.web_ui:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

The root `render.yaml` contains the same service settings and leaves `DATABASE_URL` as `sync: false` so it must be entered as a Render secret.

## Environment Variables

Set:

```text
DATABASE_URL=<Supabase SQLAlchemy URL, stored as secret>
AUTOMAP_DB_SCHEMA=automap
ALLOWED_ORIGINS=https://auto-map-cyan.vercel.app
FRONTEND_ORIGIN=https://auto-map-cyan.vercel.app
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```

Use the same Supabase direct Postgres connection string that worked locally, converted for SQLAlchemy:

```text
postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres
```

Do not expose `DATABASE_URL` to the Vercel frontend. Do not use `NEXT_PUBLIC_SUPABASE_URL` as the backend database URL. Do not use a Supabase service role key for this backend database connection.

## After Deploy

The Supabase database has already been initialized locally. If a fresh database is attached later, run:

```bash
python -m app.main --deployment-init-db
python -m app.main --deployment-seed-catalog
```

Then verify:

```text
https://YOUR-RENDER-BACKEND/api/health
https://YOUR-RENDER-BACKEND/api/status
```

No real ArcGIS publish is enabled by this deployment.

## Dashboard Flow

If a Render API token is not configured locally:

1. Open Render Dashboard.
2. Click New.
3. Choose Blueprint or Web Service.
4. Connect `khoi9034/AutoMap`.
5. Use the root `render.yaml` if using Blueprint.
6. Enter `DATABASE_URL` as a secret.
7. Deploy.
