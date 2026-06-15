# Draft Review Packets

AutoMap v0.5 creates local review packets for draft map requests.

Review packets help GIS staff inspect selected layers, filters, warnings, missing data, and draft WebMap JSON before anything is published. Packets are local-only artifacts under `outputs/review_packets/`, which is ignored by Git.

## What A Packet Contains

Each packet folder includes:

- `recipe.json`
- `webmap.json`
- `review_summary.md`
- `warnings.json`
- `layer_review.json`
- `review.html`

The HTML file is a lightweight dashboard for review. It does not require ArcGIS login, does not publish a web map item, and does not fetch full feature datasets.

## Warning Groups

`warnings.json` groups review issues into:

- `layer_selection_warnings`
- `filter_warnings`
- `symbology_warnings`
- `missing_data_warnings`
- `historical_data_warnings`
- `publishing_blockers`

Publishing blockers include reminders that no ArcGIS item was published and that review approval is required before a future publishing phase.

## Commands

```bash
python -m app.main --make-review-packet "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-review-packet "Show commercial zoning around Concord."
python -m app.main --make-review-packet "Map recent permits and planning cases near Kannapolis."
python -m app.main --make-review-packet "Show 2014 parcels and zoning."
python -m app.main --validate-review-packet outputs/review_packets/<packet-folder>
```

## Validation

Packet validation checks that required files exist, the WebMap JSON has operational layers, every operational layer has a title and URL, warnings and missing data are preserved, and generated files do not include secrets or protected database references.

## Project Boundaries

AutoMap uses its own local database and schema. The CFS database is separate and must not be touched by AutoMap review packet generation.
