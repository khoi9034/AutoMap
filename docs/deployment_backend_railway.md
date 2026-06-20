# Deploy Backend on Railway

AutoMap's backend is the FastAPI app in `app.web_ui:app`.

## Railway Service

Use:

```text
Install Command: pip install -r requirements.txt
Start Command: uvicorn app.web_ui:app --host 0.0.0.0 --port $PORT
```

Set the environment variables from `docs/deployment_backend_env.md`.

## Supabase Database

Set `DATABASE_URL` to the Supabase direct Postgres URI converted for SQLAlchemy:

```text
postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres
```

Railway should not receive Supabase frontend keys unless a separate feature explicitly requires them. The frontend must never receive the database password or service role key.

## Initialize

Run:

```bash
python -m app.main --deployment-init-db
python -m app.main --deployment-seed-catalog
```

These commands are metadata/table setup only. They do not bulk-ingest datasets, touch CFS, or publish ArcGIS items.
