# Deploy Backend on Render

AutoMap's backend is the FastAPI app in `app.web_ui:app`.

## Render Service

Use a Web Service with:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.web_ui:app --host 0.0.0.0 --port $PORT
```

Set the environment variables from `docs/deployment_backend_env.md`.

## Database

Use the Supabase direct Postgres connection string as `DATABASE_URL`:

```text
postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres
```

Do not use the Supabase public project URL, publishable key, or service role key as `DATABASE_URL`.

## After Deploy

Run a one-time shell command from Render, or locally against the production env:

```bash
python -m app.main --deployment-init-db
python -m app.main --deployment-seed-catalog
```

Then verify:

```text
https://YOUR-RENDER-BACKEND/api/status
```

No real ArcGIS publish is enabled by this deployment.
