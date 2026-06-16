# Source Coverage Model

AutoMap v2.6 adds a structured `source_coverage` object to map recipes so reviewers can see exactly how external sources are being used.

## Source Roles

`official`

An approved active source that can satisfy its verified use case and coverage.

`proxy`

A contextual source that suggests activity but is not an official approval, permit, or completed-development record. Accela or plan-review layers are proxy sources.

`reference`

A context layer used to support map interpretation. AADT and STIP are reference/context layers for transportation, not development pipeline sources.

`limited_coverage`

A source that can support a bounded geography or municipal request, but should not be treated as countywide. Concord planning cases are limited coverage.

`historical_fallback`

A legacy or year-specific layer that should only be used for historical requests unless a reviewer explicitly approves fallback use.

`needs_review`

A source that cannot be treated as approved or authoritative without human review.

## Recipe Shape

Recipes include:

```json
{
  "source_coverage": {
    "official_sources": [],
    "proxy_sources": [],
    "limited_coverage_sources": [],
    "reference_sources": [],
    "historical_fallback_sources": [],
    "missing_official_sources": [],
    "selected_source_roles": {},
    "warnings": []
  }
}
```

Each selected external source records:

- source role
- source status
- approval status
- coverage geography
- limitation
- related data gaps
- whether it resolves, partially supports, or only provides context

## Gap Rules

- `current_permits` is not resolved by Accela, plan reviews, AADT, STIP, or legacy yearly layers.
- `current_planning_cases` can be partially supported by a Concord-only planning case layer for Concord requests, with a coverage warning.
- `current_development_pipeline` can be partially supported by plan-review or Accela proxy activity, but proxy support is never official approval.
- AADT supports traffic and high-traffic corridor context.
- STIP supports planned transportation project context.

## Labels in Outputs

AutoMap labels source usage in WebMap drafts, review packets, reports, and frontend panels.

Examples:

- `Plan Reviews / Accela Activity (Proxy)`
- `Concord Planning Cases (Limited Coverage)`
- `NCDOT AADT Traffic Counts`
- `NCDOT STIP Projects`

## Parcel Context

AutoMap v3.0 reuses the same source coverage object in parcel-centered recipes and reports. When selected parcel GeoJSON is generated, it is labeled as a local derived review output, while Tax Parcels, zoning, flood, schools, roads, AADT, STIP, proxy activity, and limited-coverage planning sources keep their normal source roles and warnings.

Parcel context maps can include official context layers such as Tax Parcels, Addresses, Zoning, Municipal District, ETJ Boundary, Flood Hazard layers, School Districts, roads, AADT, and STIP. Development and planning activity layers retain their proxy or limited-coverage labels:

- Accela and plan-review activity remain proxy context.
- Concord planning cases remain limited coverage.
- Current permits remain unresolved unless an official verified source is added.

Parcel reports include source coverage warnings so reviewers can distinguish official context from proxy activity and missing official data.

## Safety

Source coverage is metadata and review context only. AutoMap does not publish real ArcGIS items, require ArcGIS login, ingest full datasets, or connect to CFS.
