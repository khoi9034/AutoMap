# Derived GeoJSON Preview

AutoMap can render local derived GeoJSON outputs in the Map Composer preview. These outputs are created only under approved ignored output folders:

- `outputs/proximity`
- `outputs/parcel_context`
- `outputs/analysis`

The backend serves them through safe API routes:

- `GET /api/local-outputs/geojson/{output_type}/{file_id}`
- `GET /api/local-outputs/metadata/{output_type}/{file_id}`

The `file_id` is an encoded repository-relative path. The server rejects path traversal, files outside approved output folders, non-GeoJSON files for the GeoJSON route, and protected markers such as secrets or environment values.

Composer preview configs can include `derived_overlays` for result layers such as origin points, target facilities, straight-line distance lines, and selected parcels. The frontend fetches these local GeoJSON files and renders them directly in the composer preview. REST layers remain context layers only.

Derived GeoJSON is draft-only. It is not uploaded to ArcGIS, not shared publicly, and not an official GIS layer.
