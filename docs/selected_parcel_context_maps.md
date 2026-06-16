# Selected Parcel Context Maps

Selected parcel context maps use a safely matched parcel set as the focus for a draft GIS review map.

## Local Selected Parcel Output

When a parcel set has a safe match count, AutoMap can fetch only the matched parcel geometries and write:

```text
outputs/parcel_context/<timestamp>_<parcel_set_slug>/
  selected_parcels.geojson
  parcel_match_receipt.json
  parcel_context_summary.md
```

The default selected-geometry limit is 100 parcels. The hard max is 250 parcels. Larger sets are blocked and should be split before geometry retrieval.

## Context Layers

Selected parcel context maps can include:

- zoning
- floodway, 100-year floodplain, and 500-year floodplain
- school districts
- roads and centerlines
- AADT and STIP context
- addresses
- Accela / plan-review proxy layers when requested
- Concord planning cases when relevant, with limited-coverage warnings

Proxy and limited-coverage sources remain clearly labeled. They do not become official approvals or official countywide development activity.

## Map Recipe Integration

When `selected_parcels.geojson` exists, AutoMap adds a derived local layer to the parcel context recipe:

- layer title: `Selected Parcels - Parcel Context`
- source status: `local_derived`
- badge/context: derived local selected parcel output
- map title: `Selected Parcels Context Map`

If the frontend preview cannot render the local GeoJSON directly, the workflow still shows the output path, layer panel item, and downloadable local file reference.

## Boundaries

Selected parcel outputs are local draft review artifacts. They are not official GIS layers, are not uploaded to Portal, and are ignored by Git. CFS remains separate and untouched.
