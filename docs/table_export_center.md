# Table Export Center

The Table Center at `/tables` lets reviewers plan and export bounded attribute tables without forcing a map workflow.

## Supported Outputs

When a table recipe is safe to export, AutoMap writes a local package under `outputs/tables/<timestamp>_<slug>/`:

- `table_preview.json`
- `table_export.csv`
- `table_export.json`
- `table_summary.md`
- `export_manifest.json`

These outputs are local draft files and are ignored by Git.

## Frontend Workflow

The Table Center shows:

- prompt input and sample table requests
- table recipe summary
- verified source layers
- selected fields
- estimated row count
- safety status
- returnGeometry=false preview rows
- CSV/JSON/Markdown export links when safe
- blocked export warnings and refinement suggestions

If a user enters a pure table prompt in Map Composer, AutoMap offers to open Table Center. If a prompt asks for both a map and a table, Map Composer can keep the map preview while adding table context.

## Export Limits

AutoMap does not silently export huge tables. Broad requests are preview-only or blocked until a reviewer narrows the request.

## Data Honesty

Table exports are based on verified catalog layers and field profiles. Missing current permits, planning gaps, and proxy development sources remain labeled honestly instead of being treated as official records.
