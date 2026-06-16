# External Source Connectors

AutoMap v2.4 added a connector framework for approved and candidate non-OpenData REST sources. AutoMap v2.5 adds real source discovery and verification on top of that framework. AutoMap v2.6 adds source usage intelligence so verified sources are selected with clear official, proxy, reference, and limited-coverage labels. The workflow is deliberately conservative: it can inspect metadata, fields, counts, and tiny non-geometry samples, but it does not ingest full feature datasets or publish anything.

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
- tiny `returnGeometry=false` attribute samples for review
- verification status

AutoMap does not download full geometries during source inspection.

## Discovery And Verification

```bash
python -m app.main --discover-sources
python -m app.main --discover-sources --keyword AADT
python -m app.main --discover-sources --keyword STIP
python -m app.main --verify-external-source ncdot_aadt_reference
python -m app.main --verify-all-external-sources
```

Discovery reports are written under `outputs/source_discovery/`, which is ignored by Git.

## Catalog Integration

If a candidate source is an ArcGIS REST layer or service and its metadata endpoint verifies successfully, AutoMap can add it to `automap.layer_catalog` with clear metadata:

- `source_key`
- `source_status`
- `approval_status`
- `known_limitations`
- aliases and planning use cases

Proxy layers remain proxy/context layers. They cannot silently become official permit or development approval layers.

v2.6 catalog semantics add richer aliases and planning use cases for:

- AADT traffic context
- STIP planned transportation project context
- Accela or plan-review proxy activity
- Concord-limited planning cases

These semantics improve matching, but source status still controls warnings and gap resolution.

## Current Candidate Areas

The seed registry includes verified or reviewable records for:

- current permits
- current planning cases
- plan review / Accela pipeline signals
- development pipeline proxy sources
- AADT traffic counts
- STIP transportation projects
- utility context proxy sources

Known unknown URLs are left as placeholders instead of invented. Current permits still need an official verified source. Concord planning cases are limited coverage, and Accela plan reviews are proxy/context only.

## API

```text
GET /api/external-sources
POST /api/external-sources/load
POST /api/external-sources/inspect
POST /api/external-sources/discover
POST /api/external-sources/verify
POST /api/external-sources/verify-all
GET /api/data-gaps/{gap_key}/candidates
POST /api/data-gaps/resolve
```

Responses are sanitized and do not expose `.env` values, database URLs, ArcGIS credentials, or real publish actions.
