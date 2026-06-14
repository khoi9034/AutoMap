# Data Gap Registry

AutoMap records requested-but-missing data needs in `automap.data_gap_registry`.

Examples:

- `current_permits`
- `current_planning_cases`
- `current_development_pipeline`
- `subdivision_activity`

Data gaps are created when a recipe asks for a topic that is not available in the verified layer catalog. This keeps recipes honest: AutoMap reports missing data instead of inventing layers, fields, URLs, or sources.

## Command

```bash
python -m app.main --list-data-gaps
```

`.env` remains local-only and must not be committed. CFS uses a separate database and was not touched.
