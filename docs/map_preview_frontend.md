# Frontend Map Preview

AutoMap v1.6 upgrades `/map-preview` into a review-focused draft preview workspace.

## Preview Source

The page uses local packet metadata from:

- `GET /api/packets`
- `GET /api/preview-config/{packet_id}`
- the existing backend preview route at `/preview/{packet_id}`

The frontend does not ingest geometries, download full feature datasets, require ArcGIS login, or publish ArcGIS items.

## Component Structure

- `frontend/components/arcgis-map-preview.tsx`
- `frontend/components/layer-panel.tsx`
- `frontend/components/warning-panel.tsx`
- `frontend/components/map-preview-client.tsx`

`arcgis-map-preview.tsx` loads preview config and embeds the local backend preview page. This preserves the existing safe backend rendering path while improving the product shell around it.

## Layer Review Panel

The layer panel shows:

- layer title
- role
- source status
- visibility
- opacity
- confidence, when available
- definition expression
- warning count
- REST layer link

For MapServer sublayers, the panel preserves the configured `service_url` and `layer_id` when a direct `layer_url` is not provided. It does not assume layer `0`.

## Warning Review Panel

Warnings are grouped into:

- missing data
- filter review
- layer selection
- publishing blockers
- historical data
- safety warnings

This keeps human review visible before adjustments, approval, or dry-run publishing.

## Publishing Safety

The preview page is draft-only. It creates no ArcGIS item, performs no public or organization sharing, and exposes no real publish button. Real publishing remains guarded CLI-only.
