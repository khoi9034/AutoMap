# Development and Transportation Intelligence

AutoMap v2.6 teaches the recipe engine how to use verified external sources without overstating what those sources mean.

## Development Activity

Development-related sources are separated into official, proxy, and limited-coverage roles.

- Current permits remain an unresolved official data gap unless a verified official current permit layer exists.
- Accela or plan-review activity may be used as a development activity proxy only.
- Proxy activity can support early planning context, but it is not permit issuance, entitlement approval, completed development, or capacity.
- Concord planning cases can support Concord-focused planning case requests, but they are labeled as limited coverage and must not be described as countywide.

Example behavior:

```bash
python -m app.main --make-recipe "Show high traffic corridors and nearby development activity."
python -m app.main --make-recipe "Show current permits near Kannapolis."
python -m app.main --make-recipe "Show planning cases around Concord."
```

Expected output:

- development-pressure requests may include plan-review/Accela as a proxy layer
- current permit requests keep `current_permits` as `needs_review` when no official current permit layer exists
- Concord planning requests select the Concord planning source when available and warn about limited coverage

## Transportation Context

Transportation sources are also role-labeled.

- AADT is traffic-volume context for high-traffic corridor and site-access review.
- STIP is planned transportation project context.
- AADT and STIP are not development pipeline layers and do not resolve development activity gaps.

Example behavior:

```bash
python -m app.main --make-recipe "Map commercial growth opportunities near high traffic roads."
python -m app.main --make-recipe "Show planned road projects near development pressure areas."
```

Expected output:

- high-traffic requests select verified AADT when available
- planned-road-project requests select verified STIP when available
- development pressure still carries proxy and missing-official-data warnings when no official development source exists

## Review Outputs

Recipes, WebMap drafts, review packets, and reports now include source coverage metadata:

- official sources
- proxy sources
- reference sources
- limited-coverage sources
- historical fallback sources
- missing official sources
- standardized source warnings

No full datasets are downloaded, no ArcGIS item is published, and no ArcGIS login is required.

## CFS Separation

AutoMap uses its own database and schema. The CFS database `cfs_dev` is separate and must not be touched by AutoMap.
