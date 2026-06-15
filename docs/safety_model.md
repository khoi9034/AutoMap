# AutoMap Safety Model

AutoMap v1.0 is a local demo and review application. It is designed to create draft GIS artifacts for human review, not official maps.

## Database Boundary

AutoMap uses its own local PostGIS database and the `automap` schema.

The CFS database `cfs_dev` is separate and must not be connected to, inspected, modified, migrated, or written by AutoMap.

## Publishing Boundary

AutoMap does not publish anything by default.

The local UI supports dry-run publishing only. Dry-run mode writes `publish_receipt.json` and does not create an ArcGIS item.

Real ArcGIS publishing remains a guarded CLI-only path and requires explicit confirmation. AutoMap does not publish publicly, does not share to the organization, and does not overwrite or delete existing ArcGIS items.

## Data Boundary

AutoMap uses verified ArcGIS REST metadata and local review JSON files.

AutoMap does not:

- ingest full geometries into PostGIS
- download full feature datasets
- require ArcGIS login for preview or review
- use an external LLM API
- commit `.env` files or secrets

## Review Boundary

All recipes, WebMap drafts, review packets, adjusted packets, and preview maps are draft-only. Human GIS review is required before any official use.
