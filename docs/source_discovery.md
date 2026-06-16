# Source Discovery

AutoMap v2.5 adds metadata-only ArcGIS REST discovery for external source candidates.

Discovery starts from known public REST roots:

- `https://location.cabarruscounty.us/arcgisservices/rest/services`
- `https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData`
- `https://maps2.concordnc.gov/server/rest/services`
- `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services`
- `https://gis11.services.ncdot.gov/arcgis/rest/services`

## What Discovery Does

- Reads ArcGIS service folder metadata.
- Searches service names by keywords such as permits, planning, Accela, AADT, and STIP.
- Inspects candidate service and layer metadata.
- Reads fields, geometry type, domains where exposed, and supported query capabilities.
- Runs count-only checks where supported.
- Reads only tiny `returnGeometry=false` attribute samples for review.
- Writes local discovery reports under `outputs/source_discovery/`.

## What Discovery Does Not Do

- It does not download full feature datasets.
- It does not download geometries.
- It does not bulk-ingest data.
- It does not publish anything.
- It does not require ArcGIS login.
- It does not treat proxy data as official permits, planning approvals, or development capacity.

## CLI

```bash
python -m app.main --discover-sources
python -m app.main --discover-sources --keyword permits
python -m app.main --discover-sources --keyword planning
python -m app.main --discover-sources --keyword accela
python -m app.main --discover-sources --keyword AADT
python -m app.main --discover-sources --keyword STIP
```

## Verification

Discovered URLs should be curated into `data/external_rest_sources.seed.json` only when they are real REST layer or service endpoints. Verification then updates `automap.external_source_registry` and upserts verified metadata into `automap.layer_catalog`.

```bash
python -m app.main --load-external-sources
python -m app.main --verify-external-source ncdot_aadt_reference
python -m app.main --verify-all-external-sources
```

Verification remains metadata-only and records `downloaded_geometry=false`.

## CFS Boundary

AutoMap discovery uses only the AutoMap repository and AutoMap database. It does not connect to CFS, does not inspect `cfs_dev`, and does not use CFS ports.
