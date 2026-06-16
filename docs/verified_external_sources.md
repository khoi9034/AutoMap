# Verified External Sources

AutoMap v2.5 replaced several placeholder source candidates with real verified REST endpoints where possible. These sources are stored in `data/external_rest_sources.seed.json` and verified into the AutoMap database only.

AutoMap v2.6 uses these verified sources through the source coverage model. Verification means the REST metadata exists and can be trusted as catalog metadata; it does not automatically mean a source is official for every planning use.

## Verified Reference / Proxy Sources

| Source key | Source | Status | Use | Notes |
| --- | --- | --- | --- | --- |
| `cabarrus_accela_plan_review_proxy` | Cabarrus Current Accela Plan Reviews | candidate, proxy | Development pipeline context | Verified REST layer, but proxy only. Not official permit issuance, entitlement approval, or final development approval. |
| `concord_planning_cases_limited_candidate` | Concord Planning Cases | candidate, active | Limited planning case context | Verified REST layer, but coverage is limited to Concord unless confirmed otherwise. Does not resolve countywide planning cases. |
| `ncdot_aadt_reference` | NCDOT 2024 AADT Stations | approved, reference | Traffic count context | Verified NCDOT reference layer. Supports traffic/high traffic corridor requests. Not development pipeline data. |
| `ncdot_stip_reference` | NCDOT 2026-2035 STIP Projects | approved, reference | Planned transportation project context | Verified NCDOT service with point and line layers. Not development approval or parcel suitability by itself. |

## Current Gap Status

- `current_permits`: still `needs_review`. No official current permit layer has been verified.
- `current_planning_cases`: `partially_supported` by a Concord-only planning case layer. Countywide coverage is not resolved.
- `current_development_pipeline`: `partially_supported` by the Cabarrus Accela plan-review proxy. It remains proxy/context only.

## Catalog Integration

Verified REST metadata can be upserted into `automap.layer_catalog` with:

```bash
python -m app.main --verify-all-external-sources
```

Verified source upserts from v2.5:

- Cabarrus Accela plan-review proxy layer
- Concord planning cases layer
- NCDOT AADT station layer
- NCDOT STIP points layer
- NCDOT STIP lines layer

These are trusted catalog metadata records, but their approval/source statuses still control whether recipes may select them and how warnings are shown.

## v2.6 Usage Rules

- AADT is selected for traffic, AADT, high-traffic, and road-volume requests as transportation context.
- STIP is selected for planned road project and transportation project requests as reference context.
- Accela and plan-review layers can support development pressure as proxy context only.
- Concord planning cases can support Concord planning case requests, but they remain limited coverage.
- Current permits remain unresolved until an official current permit source is verified.

Recipe, WebMap, review packet, report, and frontend outputs expose those roles through `source_coverage` and visible proxy/reference/limited-coverage labels.

## Safety Notes

- No full datasets are ingested.
- No feature geometries are downloaded during discovery or verification.
- Generated discovery reports are ignored by Git.
- Nothing is published to ArcGIS Online, Enterprise, or Portal.
- CFS and `cfs_dev` remain separate and untouched.
