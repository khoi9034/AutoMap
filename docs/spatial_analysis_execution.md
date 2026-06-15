# Spatial Analysis Execution

AutoMap v2.3 adds summary analytics reports on top of user-guided refinement, safe bounded spatial execution, and the bounded spatial query optimizer.

The first fully supported operation is:

```text
Select parcels in a requested geography that intersect a constraint layer.
```

Example:

```bash
python -m app.main --plan-analysis "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --execute-analysis "Show parcels in Concord that are in the 100-year floodplain."
```

## Supported Operations

Fully implemented:

- `filter_by_geography`
- `select_by_intersection`
- `attribute_filter_only`

Stubbed with review-needed blocking:

- `select_by_distance`
- `exclude_by_intersection`
- `summarize_by_boundary`

Unsupported or ambiguous requests return `executable=false` with a clear reason.

## Execution Flow

For a parcel/flood/geography request, AutoMap:

1. Builds a recipe from the trusted layer catalog.
2. Identifies the geography, parcel, and constraint layers.
3. Runs count-only REST checks first.
4. Fetches only bounded geography and constraint geometry.
5. Uses server-side spatial filters to query candidate parcel ObjectIDs against the constraint geometry.
6. Deduplicates parcel ObjectIDs and enforces download limits.
7. Downloads parcel geometry only when the final ObjectID count is safe.
8. Performs local Shapely intersection.
9. Writes a local GeoJSON result under `outputs/analysis/`.
10. Records an analysis receipt in the AutoMap database.

If the optimized candidate count still exceeds the safety limit, AutoMap blocks execution and can create a refinement session instead of downloading geometry.

Outputs are local review artifacts only. They are not official GIS layers.

## Output Files

Each run writes:

- `analysis_result.geojson`
- `analysis_receipt.json`
- `input_recipe.json`
- `analysis_summary.md`

The receipt includes target/geography/constraint layers, where clauses, broad count, optimized candidate count, ObjectID count, chunk receipts, feature limits, output count, warnings, narrowing suggestions, and no-publish status.

Blocked runs can also produce refinement outputs under `outputs/analysis_refinements/`:

- `refinement_summary.json`
- `refinement_summary.md`
- `refinement_receipt.json`
- optional `batch_plan.json`
- optional `batch_receipt.json`
- optional `object_id_list.json`

## Frontend

The Next.js frontend includes `/analysis`.

The page can:

- plan analysis feasibility
- execute supported bounded analysis
- show blocked reasons
- show broad and optimized counts
- show query strategy and chunks
- show safety limits and narrowing suggestions
- create refinement options for blocked runs
- execute summary-only refinements without geometry download
- generate analysis report packages from analysis/refinement results
- show output count
- link to local GeoJSON
- pass a derived local result to the Map Preview layer panel

Derived outputs are marked as `Derived Local Analysis Result`.

## Safety

AutoMap does not bulk-ingest datasets, does not publish derived GeoJSON, does not upload to ArcGIS Online or Portal, and does not require ArcGIS login.

The CFS database is separate and untouched.

See `docs/spatial_query_optimizer.md` for the v2.1 optimizer details.
See `docs/analysis_refinement.md` for the v2.2 blocked-analysis refinement workflow.
See `docs/analysis_summary_reports.md` for the v2.3 summary analytics report workflow.
