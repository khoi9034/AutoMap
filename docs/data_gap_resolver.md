# AutoMap Data Gap Resolver

AutoMap v2.4 added a local data gap resolver for recurring gaps. AutoMap v2.5 adds real source verification so those gaps can show verified, partial, or still-open status. AutoMap v2.6 adds source-coverage intelligence so recipes can show exactly which selected layers are official, proxy, reference, limited coverage, historical fallback, or missing official sources:

- `current_permits`
- `current_planning_cases`
- `current_development_pipeline`

Related transportation context sources are tracked separately:

- `traffic_counts`
- `stip_projects`

The resolver does not make missing data disappear. It maps each gap to approved, candidate, or needs-review external source records and explains whether a source is authoritative, proxy/context only, limited by geography, or still uninspected.

Recipe outputs now include a `source_coverage` object. It preserves unresolved official gaps even when proxy or reference layers are selected for context.

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
python -m app.main --discover-sources --keyword planning
python -m app.main --verify-all-external-sources
python -m app.main --resolve-data-gaps
python -m app.main --gap-candidates current_permits
python -m app.main --gap-candidates current_planning_cases
python -m app.main --gap-candidates current_development_pipeline
```

## Resolution Behavior

An approved, active, verified source can resolve a gap.

A proxy source can be included as optional context with warnings, but it does not resolve official permit, planning case, or development pipeline gaps.

Partial support is explicit:

- Concord-only planning cases can partially support current planning context, but do not resolve countywide planning cases.
- Cabarrus Accela plan reviews can partially support development-pipeline context, but do not resolve official current permits.
- AADT and STIP are transportation context only, not development pipeline sources.

For Concord planning case requests, the Concord source may be selected as limited coverage and the recipe warns reviewers not to imply countywide coverage. For current permits near Kannapolis, AutoMap keeps the official permit gap visible because no official current permit layer is verified.

A candidate or needs-review source remains reviewable evidence only. AutoMap records it in `automap.data_gap_resolution_log` and keeps the relevant missing-data warning visible.

## Frontend

The Data Gaps page shows candidate sources, source scores, approval status, source status, limitations, and review actions. The External Sources page shows the source registry and inspection metadata.
