# Exhibit Exports

AutoMap v4.1 can generate local county exhibit packages from preview-ready Map Composer sessions.

Exhibit packages are intended for draft GIS review artifacts such as planning staff memo figures, zoning review exhibits, parcel context maps, fire station proximity exhibits, and internal GIS request responses.

## Supported Layout Types

- `proximity_exhibit`
- `parcel_context_exhibit`
- `flood_exposure_exhibit`
- `zoning_context_exhibit`
- `scenario_exhibit`
- `general_reference_exhibit`

AutoMap chooses the layout type from the composer request type, prompt, title, and proximity metadata.

## Local Package Contents

Generated packages are written under ignored local folders:

```text
outputs/exhibits/<timestamp>_<slug>/
  exhibit.html
  exhibit_data.json
  layer_sources.csv
  warnings.json
  export_manifest.json
```

The package includes a professional title block, key findings, source notes, layer source table, warning summary, draft disclaimer, and links to local files where appropriate.

## Safety

Exhibit exports are local and draft-only. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not upload local GeoJSON, and does not expose secrets. Generated files stay ignored by Git.

PDF generation is not forced in v4.1. Use the browser print-to-PDF workflow from the print layout when a PDF is needed.

## API

```text
POST /api/exhibits/generate
GET /api/exhibits
GET /api/exhibits/{exhibit_id}
GET /api/exhibits/{exhibit_id}/html
```

The generator requires a preview-ready composer session. Blocked parcel/address previews should be corrected before exhibit export.

## Composer Integration

The Map Composer Print / Export step exposes:

- Open Print Layout
- Generate Exhibit Package
- Export WebMap JSON
- Export Layer Source CSV
- Export Warning Summary

These are all local draft outputs. They are not official county maps.

CFS remains separate and untouched.
