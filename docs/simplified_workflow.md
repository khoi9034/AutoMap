# Simplified Workflow

AutoMap v3.2 adds a guided `/workflow` page for the normal local review path:

```text
Prompt -> Recipe -> Map Preview -> Adjust -> Analysis/Report -> Print/Export
```

The workflow page keeps the primary actions in one place:

- generate a recipe from a prompt
- review selected layers, warnings, missing data, and parcel match status
- create a local review packet and preview when the request is ready
- adjust the draft through the existing human adjustment loop
- run analysis only when it is explicitly useful and safe
- generate local draft reports/exports

## Parcel Requests

Parcel-centered prompts are treated as context-map requests first. A prompt such as:

```text
Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.
```

does not automatically become an analysis execution request. AutoMap first parses and tries to match the parcel/PIN/address against verified parcel fields.

If the parcel is matched safely, AutoMap can fetch only the matched parcel geometry, compute a small buffered extent, add a local selected-parcel layer, and focus the preview on the parcel.

If the parcel is not matched, the workflow shows `Parcel not matched`, disables parcel-focused preview, and asks the user to correct the parcel/PIN/address. AutoMap does not zoom to a countywide fallback and does not pretend a selected parcel map is ready.

## Analysis

Analysis remains optional. For basic parcel context maps, the workflow says analysis is not needed unless the reviewer asks for an operation such as intersection, proximity, or summary execution. Any execution still goes through existing safety limits and blocked/refinement behavior.

## Export

The workflow can create local review packets and local report/export artifacts. These are draft review files only. They are not official print maps, do not publish to ArcGIS, and do not require ArcGIS login.

## Boundaries

AutoMap uses ports `3010` and `8010`. CFS keeps ports `3000` and `8000`. AutoMap does not connect to `cfs_dev`, does not bulk-ingest parcels, and does not publish real ArcGIS items from the frontend.
