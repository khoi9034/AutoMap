# AutoMap Database Setup

Project: AutoMap

## Local Database

- Host: `localhost`
- Port: `5433`
- Database: `automap`
- Schema: `automap`
- PostGIS enabled: yes
- Health check table: `automap.project_database_check`

## CFS Boundary

CFS uses the separate database `cfs_dev` and must not be modified by AutoMap setup. Do not connect AutoMap tooling to `localhost:5433/cfs_dev`, do not inspect CFS tables, and do not run CFS migrations from this project.

## Local Environment

Create a local `.env` from `.env.example`, then replace `YOUR_LOCAL_POSTGRES_PASSWORD` with the local PostgreSQL password:

```bash
cp .env.example .env
```

`.env` is local-only and must not be committed.

## Verification

After credentials are filled in and PostgreSQL/PostGIS is available, run:

```bash
python -m app.main --check-db
```
