# AutoMap Data Gap Resolver

AutoMap v2.4 adds a local data gap resolver for the recurring gaps that appear in county GIS requests:

- `current_permits`
- `current_planning_cases`
- `current_development_pipeline`

The resolver does not make missing data disappear. It maps each gap to approved, candidate, or needs-review external source records and explains whether a source is authoritative, proxy/context only, limited by geography, or still uninspected.

## Safety Rules

- AutoMap does not connect to CFS or `cfs_dev`.
- AutoMap does not bulk-ingest feature datasets.
- Metadata inspection is limited to REST metadata, fields, domains, counts, and non-geometry checks.
- Proxy sources are not official development approvals, permit issuance, utility capacity, or final planning actions.
- Candidate sources must be reviewed before they can resolve an official data gap.

## CLI

```bash
python -m app.main --load-external-sources
python -m app.main --inspect-external-sources
python -m app.main --resolve-data-gaps
python -m app.main --gap-candidates current_permits
python -m app.main --gap-candidates current_planning_cases
python -m app.main --gap-candidates current_development_pipeline
```

## Resolution Behavior

An approved, active, verified source can resolve a gap.

A proxy source can be included as optional context with warnings, but it does not resolve official permit, planning case, or development pipeline gaps.

A candidate or needs-review source remains reviewable evidence only. AutoMap records it in `automap.data_gap_resolution_log` and keeps the relevant missing-data warning visible.

## Frontend

The Data Gaps page shows candidate sources, source scores, approval status, source status, limitations, and review actions. The External Sources page shows the source registry and inspection metadata.
