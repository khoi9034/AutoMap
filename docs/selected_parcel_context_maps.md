# Selected Parcel Context Maps

Selected parcel context maps use a safely matched parcel set as the focus for a draft GIS review map.

AutoMap v3.2 prevents unmatched parcel prompts from displaying a broad county map as if the parcel were selected. The preview must have a matched parcel and selected parcel geometry before it can use parcel focus mode.

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

- layer title: `Selected Parcel`
- source status: `derived_local`
- badge/context: derived local selected parcel output
- map title: `Selected Parcels Context Map`
- suggested extent: selected parcel buffered extent

If the frontend preview cannot render the local GeoJSON directly, the workflow still shows the output path, layer panel item, and downloadable local file reference.

If the parcel is unmatched, AutoMap sets `preview_status=blocked_until_parcel_matched`, does not create selected parcel GeoJSON, and asks the user to correct the parcel/PIN/address before preview or analysis continues.

AutoMap v3.6 adds direct composer rendering for selected parcel GeoJSON when it exists. The selected parcel appears as a local derived overlay with a highlighted outline. If an address is matched but the parcel is not resolved, the composer shows the address point and any proximity line but does not draw or imply a selected parcel outline.

## Proximity Integration

AutoMap v3.1 can use a safely matched parcel/address as the origin for nearest-facility and route-draft workflows. Proximity outputs are written separately under `outputs/proximity/` and are labeled as draft local review artifacts.

## Boundaries

Selected parcel outputs are local draft review artifacts. They are not official GIS layers, are not uploaded to Portal, and are ignored by Git. CFS remains separate and untouched.
