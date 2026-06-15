# Analysis Refinement

AutoMap v2.2 adds user-guided refinement for blocked spatial analysis runs.

Blocked analysis is not a failure. It means AutoMap counted first, found that the request would exceed safe local download limits, and stopped before downloading too much geometry.

## Purpose

When an optimized analysis count is still too high, AutoMap creates a refinement session with reviewable options:

- `summary_only`
- `split_batches`
- `narrow_constraint`
- `attribute_filter`
- `smaller_geography`
- `object_id_only`
- `unsupported`

The reviewer chooses a safer path instead of AutoMap silently raising limits or downloading broad parcel datasets.

## Summary-Only Mode

`summary_only` is fully implemented in v2.2.

It writes local review outputs under `outputs/analysis_refinements/`:

- `refinement_summary.json`
- `refinement_summary.md`
- `refinement_receipt.json`

Summary-only mode does not download parcel geometry and does not create GeoJSON. It preserves the broad count, optimized candidate count, safety limit, query strategy, chunk metadata, ObjectID count when available, and narrowing suggestions.

## Split-Batches Mode

`split_batches` creates a safe batch plan from optimizer chunks.

It does not automatically download all batches. AutoMap only records:

- batch count
- per-batch candidate counts
- hard max feature limit
- whether all batches would exceed the hard max
- review notes for future one-batch execution

## Attribute Filters

Attribute filter suggestions come only from real target-layer fields and profiled fields. AutoMap does not invent fields such as acreage, zoning, land use, or parcel type if the target layer does not expose them.

Typical suggestions may include:

- parcels over 1 acre
- parcels over 5 acres
- filter by real zoning/general-use field
- filter by real municipal/district field

## Smaller Geography

For v2.2, smaller geography suggestions are guidance only. AutoMap can suggest directional tiles such as north, south, east, or west, but it does not require custom drawing tools yet.

## CLI

```bash
python -m app.main --create-analysis-refinement <analysis_run_id>
python -m app.main --list-analysis-refinements
python -m app.main --select-analysis-refinement <session_id> summary_only --params-json "{}"
python -m app.main --execute-analysis-refinement <session_id>
```

## API

```text
POST /api/analysis/refinements
GET /api/analysis/refinements
GET /api/analysis/refinements/{session_id}
POST /api/analysis/refinements/{session_id}/select
POST /api/analysis/refinements/{session_id}/execute
```

All responses are sanitized JSON. No secrets, database URLs, ArcGIS credentials, or real publish actions are exposed.

## Frontend

The `/analysis` page shows a Refine Analysis panel when an execution result is blocked. The panel shows:

- broad count
- optimized count
- safety limit
- blocked reason
- recommended refinement options
- option tradeoffs
- parameters JSON editor
- summary-only and batch-plan output links

## Safety

AutoMap v2.2 keeps the v2.1 safety limits. It does not raise feature limits just to make execution pass.

AutoMap does not:

- bulk-ingest countywide datasets
- download all parcels in Concord when the optimized candidate count is too high
- silently bypass feature limits
- publish derived outputs
- require ArcGIS login
- touch external project databases

Generated refinement outputs are local files ignored by Git.
