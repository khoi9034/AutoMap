# Exhibit Exports

AutoMap can generate local county exhibit packages from preview-ready Map Composer sessions. v4.7 makes exhibit generation use the saved composer map state so exports preserve the exact adjusted preview state and honor the selected print/export mode.

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
  composer_map_state.json
  report_sections.json
  layer_sources.csv
  warnings.json
  export_manifest.json
```

The package includes a professional title block, key findings, warning summary, draft disclaimer, saved composer map state, configurable report sections, and links to local files where appropriate. The default `Map only` mode keeps `exhibit.html` map-first and does not force the long layer source table into the main exhibit page. `Full report` adds longer layer/source/statistics sections by default, while the live preview checkboxes control the exact included sections.

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

- Open Browser Print
- Generate Exhibit Package
- Export WebMap JSON
- Export Layer Source CSV
- Export Warning Summary

These are all local draft outputs. They are not official county maps.

Before generating an exhibit, the frontend sends the current composer map state, including adjusted title, layer order, layer visibility, opacity, route styling, reviewer notes, and report section choices.

CFS remains separate and untouched.
