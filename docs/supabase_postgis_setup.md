# Supabase PostGIS Setup

AutoMap can use Supabase Postgres/PostGIS as the production backend database. The public Supabase project URL and publishable API key are not the FastAPI database connection string.

## Safe Setup SQL

In the Supabase dashboard:

1. Open the Automap project.
2. Open SQL Editor.
3. Run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS automap;
```

If `CREATE EXTENSION` is not permitted from the backend runtime, run it in SQL Editor and then rerun the backend initialization command.

## DATABASE_URL

Go to Connect -> Direct -> Connection string and copy the PostgreSQL URI. Convert it to SQLAlchemy format by adding `+psycopg2`:

```text
postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres
```

Set that value as the backend `DATABASE_URL`.

Do not put the database password in frontend env variables. Do not use the Supabase service role key in the frontend.

## Initialize AutoMap Tables

After the backend environment is configured, run:

```bash
python -m app.main --deployment-init-db
```

The command:

- refuses the protected `cfs_dev` database
- checks the current database
- checks `SELECT PostGIS_Version();`
- creates the `automap` schema if needed
- creates AutoMap tables with `CREATE TABLE IF NOT EXISTS`
- does not drop tables
- does not publish ArcGIS items
- does not touch CFS

## Seed Catalog Metadata

After initialization, seed metadata only:

```bash
python -m app.main --deployment-seed-catalog
```

This runs the safe metadata workflow:

```bash
python -m app.main --build-catalog-from-rest
python -m app.main --profile-catalog-fields
python -m app.main --load-external-sources
python -m app.main --inspect-external-sources
python -m app.main --resolve-data-gaps
```

The seed workflow inspects REST metadata and field profiles. It must not bulk-download countywide feature datasets.
