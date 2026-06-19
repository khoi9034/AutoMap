# Map Preview Behavior

AutoMap v3.4 makes preview behavior explicit and conservative.
AutoMap v3.5 adds address-aware blockers so address prompts do not get mislabeled as parcel failures.
AutoMap v3.6 adds direct rendering for local derived GeoJSON overlays in the Map Composer.

## Parcel-Focused Prompts

If a prompt contains a parcel ID, PIN, PIN14, address, or parcel-list language, AutoMap must match the parcel before showing a parcel-focused preview.

If matched, AutoMap:

- fetches only the matched parcel geometry
- writes a local selected-parcel GeoJSON
- computes a parcel extent and buffered extent
- uses the buffered extent as the preview focus
- adds the selected parcel as a top highlight layer
- adds requested context layers underneath

If unmatched, AutoMap:

- sets `can_preview=false`
- sets `next_action=correct_parcel_identifier`
- records unmatched identifiers
- blocks the parcel-focused preview
- does not use the Tax Parcels full extent as fallback
- does not show a broad county map as successful parcel output
- does not run analysis

Address-focused prompts follow the same focused-preview rule. If the address is unmatched, AutoMap sets `can_preview=false`, shows `Address not found` guidance, and does not show a broad county map as a successful address preview.

If an address is matched and a proximity result exists, AutoMap can preview the address point, nearest facility target, and straight-line distance line even when a related parcel is not resolved. In that case it warns that the related parcel was not resolved and does not show the full Tax Parcels layer as the selected property.

## Derived Local Overlays

Composer preview configs can include `derived_overlays` for local GeoJSON outputs:

- origin address point
- selected parcel, only if resolved
- nearest facility target
- straight-line distance

These overlays are served through `/api/local-outputs/geojson/...`, rendered locally by the frontend, and never uploaded or published.

## Geography-Focused Prompts

For prompts that mention Concord, Harrisburg, Kannapolis, Midland, Mount Pleasant, Locust, Cabarrus County, or countywide, AutoMap uses a focused review extent when available. Boundary filters still require review when field matching is uncertain.

## Layer Display Rules

Preview metadata records:

- visibility
- opacity
- draw order
- layer role
- display role: target, context, constraint, proxy, reference, selected result
- definition expression

Target layers and selected local results are visible by default. Context layers use transparent reference styling. Historical layers are not visible by default unless the user requested historical data.

## Analysis

Preview is not analysis. Basic context prompts stop at preview/export unless the user explicitly asks AutoMap to select, intersect, count, summarize, calculate, measure, or run analysis.

## Safety

Preview uses local draft artifacts only. Nothing is published to ArcGIS, no ArcGIS login is required, no bulk countywide parcel download occurs, and the CFS database remains separate and untouched.
