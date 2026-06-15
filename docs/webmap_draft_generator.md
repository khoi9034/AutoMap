# ArcGIS WebMap Draft Generator

AutoMap v0.4 converts a validated map recipe into local ArcGIS WebMap JSON.

The generator uses only the selected layers already chosen from `automap.layer_catalog`. It preserves the catalog `layer_url` and `service_url`, carries recipe confidence and review warnings into each operational layer, and uses definition expressions only when v0.3 filter planning drafted them.

## Scope

The v0.4 generator creates draft JSON files only. It does not publish to ArcGIS Online or Portal, does not require an ArcGIS login, does not download full feature datasets, and does not ingest geometries.

CFS is separate. AutoMap must not connect to or modify the CFS `cfs_dev` database.

## Layer Handling

Operational layers are generated from recipe `selected_layers`.

Each layer includes:

- `id`
- `title`
- `url`
- `serviceUrl`
- `layerUrl`
- `layerType`
- `visibility`
- `opacity`
- `itemId` when the catalog has a service item id
- `layerDefinition`
- `popupInfo`
- `showLegend`
- AutoMap metadata such as role, layer key, confidence, source status, and review warnings

MapServer sublayer URLs are preserved from the catalog. Group or non-feature service references are represented with an ArcGIS map service style layer type.

## Definition Expressions

Definition expressions are copied only from recipe `filter_plan[*].draft_where_clause`.

If a filter plan has low confidence or needs review, the expression is still included but the operational layer is marked with:

- `autoMapNeedsReview: true`
- `autoMapReviewWarnings`
- `autoMapDefinitionSource: filter_plan`

AutoMap does not invent SQL expressions.

## Renderers

Renderers are rule-based:

- Flood layers use transparent blue polygon fills.
- Parcel layers use transparent fill with bright outline, and affected-parcel titles when the recipe includes an intersect operation.
- Zoning layers use a unique-value placeholder when a zoning field is known; otherwise they use a simple transparent fill and preserve a review warning.
- School layers use a unique-value placeholder when a district/name field is known.
- Transportation layers use simple line symbols.
- Point layers use simple marker symbols.

## Layer Order

Layers are ordered bottom to top:

1. Boundary and jurisdiction layers
2. Parcels and property layers
3. Zoning, school, environmental, and terrain polygons
4. Flood and other constraint overlays
5. Roads and transportation lines
6. Point layers

## Initial Extent

AutoMap uses metadata extents only. It first prefers selected boundary or jurisdiction layer extents for named places such as Concord, Kannapolis, Harrisburg, Midland, Mount Pleasant, Locust, or Cabarrus County. If those are unavailable, it uses another selected layer extent. It never queries feature geometry to calculate an extent.

## Commands

```bash
python -m app.main --make-webmap-draft "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-webmap-draft "Show commercial zoning around Concord."
python -m app.main --validate-webmap-draft outputs/webmaps/<generated-file>.json
```

Generated drafts are written under `outputs/webmaps/`, which is ignored by Git.
