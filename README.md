# AutoMap: County GIS Request Engine

AutoMap converts plain-English county GIS map requests into structured map recipes using only approved GIS layers from a local layer catalog.

## Current Phase

v0.0 repo setup only.

This repository is intentionally independent. It does not connect to CFS or import CFS code. The current scaffold uses placeholder Python modules and mock data by default.

## Future Phases

1. Prompt-to-map-recipe engine
2. Semantic layer catalog
3. PostGIS connection
4. ArcGIS REST layer inspection
5. ArcGIS web map generator
6. Human review/edit loop
7. PDF/export tools

## Project Structure

```text
automaps/
  app/
    __init__.py
    main.py
    recipe_engine.py
    layer_matcher.py
    prompt_parser.py
    confidence.py
  data/
    layer_catalog.example.json
    test_prompts.json
  outputs/
    sample_recipes/
  tests/
    test_prompt_parser.py
    test_layer_matcher.py
    test_recipe_engine.py
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## Local Setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m pytest
```

## PostGIS Setup

AutoMap uses its own database called `automaps` and its own schema called `automap`. This is separate from CFS and should use separate credentials.

Create a local environment file from the template:

```bash
cp .env.example .env
```

Then edit `.env` so `DATABASE_URL` points to AutoMap's own PostGIS database:

```text
DATABASE_URL=postgresql+psycopg2://automap_user:your_password@localhost:5432/automaps
AUTOMAP_DB_SCHEMA=automap
```

To check the configured database connection:

```bash
python -m app.main --check-db
```

The check connects to the configured database, verifies PostGIS is available, creates the `automap` schema if it does not already exist, and reports the active schema. It does not create application tables, ingest county data, or create ArcGIS web maps.

## Notes

- Approved GIS layers will come from a local layer catalog.
- Application table creation is out of scope for v0.0.
- External GIS service inspection is out of scope for v0.0.
- Placeholder code should be replaced incrementally as each future phase begins.
