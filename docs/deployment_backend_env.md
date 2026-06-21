# Backend Deployment Environment

Set these environment variables on the backend host:

```text
DATABASE_URL=postgresql+psycopg2://postgres.mjfbpmatxvjczikqbuva:YOUR_SUPABASE_DB_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
AUTOMAP_DB_SCHEMA=automap
ALLOWED_ORIGINS=https://auto-map-cyan.vercel.app
ALLOWED_ORIGIN_REGEX=^https://(?:auto-map-cyan|auto-[a-z0-9-]+-khoi-nguyens-projects-9f6b140b)\.vercel\.app$
FRONTEND_ORIGIN=https://auto-map-cyan.vercel.app
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```

`DATABASE_URL` must use a Supabase SQLAlchemy URL for the Automap project. Store it as a backend secret only.

If Render reports a network error against the Supabase Direct host, especially an IPv6 address with `Network is unreachable`, switch Render's `DATABASE_URL` to the Supabase Session Pooler connection string from Supabase Dashboard -> Connect -> Session Pooler. Convert it to SQLAlchemy format by using `postgresql+psycopg2://...`. The pooler username should identify the project, for example `postgres.mjfbpmatxvjczikqbuva`, and the database name should remain `postgres`.

For local development, `ALLOWED_ORIGINS` can also include:

```text
http://localhost:3010,http://127.0.0.1:3010
```

`ALLOWED_ORIGIN_REGEX` is optional because AutoMap includes a restricted default for this Vercel project. Keep it restricted to `https://*.vercel.app` deployment URLs for the `auto-map` project/team, and do not use `*` in production.

Never set frontend variables to the Supabase database password or service role key.
Do not expose `DATABASE_URL` to Vercel and do not put it in any `NEXT_PUBLIC_*` variable.
Do not use `NEXT_PUBLIC_SUPABASE_URL` or a Supabase publishable key as the FastAPI database connection string.

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

## Health Checks

Render should use:

```text
/api/health
```

Expected safe response:

```json
{
  "ok": true,
  "service": "automap-api",
  "real_publish_enabled": false
}
```

## Publishing Safety

Real ArcGIS publishing remains disabled by default:

```text
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```
