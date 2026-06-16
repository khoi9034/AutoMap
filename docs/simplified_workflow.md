# Simplified Workflow

AutoMap v3.4 makes `/map-composer` the primary normal local review path:

```text
Request -> Preview -> Adjust -> Print / Export
```

The composer keeps the primary actions in one place:

- generate the technical draft-map artifacts behind the scenes from a prompt
- review selected layers, warnings, missing data, and parcel match status
- preview the map only when the request is truly focusable
- adjust the draft with simple title, layer, opacity, order, filter, and note controls
- generate local draft reports/exports

The older `/workflow`, `/map-request`, `/clarify`, `/recipe-review`, `/map-preview`, `/adjustments`, `/approval`, and `/publish-center` routes redirect to `/map-composer` by default. Normal users see the four-step composer instead of the old internal 10-step workflow.

## Parcel Requests

Parcel-centered prompts are treated as context-map requests first. A prompt such as:

```text
Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.
```

does not automatically become an analysis execution request. AutoMap first parses and tries to match the parcel/PIN/address against verified parcel fields.

If the parcel is matched safely, AutoMap can fetch only the matched parcel geometry, compute a small buffered extent, add a local selected-parcel layer, and focus the preview on the parcel.

If the parcel is not matched, the composer shows `Parcel not matched`, disables parcel-focused preview, and asks the user to correct the parcel/PIN/address. AutoMap does not zoom to a countywide fallback and does not pretend a selected parcel map is ready.

## Analysis

Analysis remains optional. For basic parcel context maps, the composer does not send the user to Analysis. Analysis is suggested only when the prompt asks to select, intersect, summarize, count, measure, or calculate, or when the reviewer clicks an analysis action manually.

## Export

The composer can create local review packets and local report/export artifacts. These are draft review files only. They are not official print maps, do not publish to ArcGIS, and do not require ArcGIS login.

## Boundaries

AutoMap uses ports `3010` and `8010`. CFS keeps ports `3000` and `8000`. AutoMap does not connect to `cfs_dev`, does not bulk-ingest parcels, and does not publish real ArcGIS items from the frontend.
