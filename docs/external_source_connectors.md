# External Source Connectors

AutoMap v2.4 adds a connector framework for approved and candidate non-OpenData REST sources. The framework is deliberately conservative: it can inspect metadata and count availability, but it does not ingest full feature datasets or publish anything.

## Source Registry

Seed records live in:

```text
data/external_rest_sources.seed.json
```

Each source records:

- `source_key`
- `source_name`
- `source_type`
- `base_url` or `layer_url`
- `priority`
- `approval_status`
- `source_status`
- `categories`
- `intended_gaps`
- `notes`
- `limitations`

Supported approval statuses:

- `approved`
- `candidate`
- `needs_review`

Supported source statuses:

- `active`
- `proxy`
- `reference`
- `legacy`

## Metadata Inspection

AutoMap can inspect:

- ArcGIS service metadata
- layer metadata
- fields and domains when exposed by REST metadata
- record counts where supported
- verification status

AutoMap does not download full geometries during source inspection.

## Catalog Integration

If a candidate source is an ArcGIS REST layer or service and its metadata endpoint verifies successfully, AutoMap can add it to `automap.layer_catalog` with clear metadata:

- `source_key`
- `source_status`
- `approval_status`
- `known_limitations`
- aliases and planning use cases

Proxy layers remain proxy/context layers. They cannot silently become official permit or development approval layers.

## Current Candidate Areas

The seed registry includes review placeholders for:

- current permits
- current planning cases
- plan review / Accela pipeline signals
- development pipeline proxy sources
- AADT traffic counts
- STIP transportation projects
- utility context proxy sources

Known unknown URLs are left as placeholders instead of invented.

## API

```text
GET /api/external-sources
POST /api/external-sources/load
POST /api/external-sources/inspect
GET /api/data-gaps/{gap_key}/candidates
POST /api/data-gaps/resolve
```

Responses are sanitized and do not expose `.env` values, database URLs, ArcGIS credentials, or real publish actions.
