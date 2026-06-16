# Parcel-Focused Preview

AutoMap v3.3 keeps parcel-centered preview behavior strict inside Map Composer. A parcel prompt cannot silently fall back to a broad county/context map.

## Preview Readiness

Every parcel-centered recipe includes a `parcel_context` block with:

- input identifiers
- match status
- matched count
- unmatched identifiers
- candidate matches
- `can_focus_map`
- `can_fetch_geometry`
- `reason_if_not_focusable`
- `preview_status`
- `analysis_status`

If `can_focus_map=false`, preview status is `blocked_until_parcel_matched`. `/map-composer` and `/map-preview` show a large warning instead of the broad map iframe.

## Matched Parcels

When a parcel match is safe, AutoMap fetches only the matched parcel geometry and writes local draft output under:

```text
outputs/parcel_context/
```

It then computes:

- `parcel_extent`
- `parcel_buffer_extent`
- `suggested_extent = parcel_buffer_extent`
- `focus_mode = parcel`
- selected parcel GeoJSON metadata for the layer panel

The selected parcel layer is drawn above context layers when local preview rendering supports it. Context layers are still shown as reference layers, but the extent is focused on the selected parcel buffer.

## Unmatched Parcels

When a parcel/PIN/address is unmatched:

- no selected parcel GeoJSON is written
- `can_focus_map=false`
- `can_fetch_geometry=false`
- `preview_status=blocked_until_parcel_matched`
- `analysis_status=blocked_until_parcel_matched`
- no countywide Tax Parcels extent is used as a fake parcel extent

The user is asked to correct the parcel ID, PIN, or address before focused preview or analysis can continue.

Map Composer returns `can_preview=false`, `next_action=correct_parcel_identifier`, and clear `preview_blockers` for this case.

## Context Layers

Zoning, floodplain, roads, schools, AADT, STIP, and proxy development layers can still appear in the recipe as requested context. They are reference layers until a selected parcel is matched and the map can focus on the parcel buffer extent.

Proxy and limited-coverage layers remain labeled as review context. They are not official approvals.

## Safety

AutoMap does not bulk-download parcels, does not query countywide geometry for a parcel preview, does not invent parcel matches, and does not publish local outputs to ArcGIS.
