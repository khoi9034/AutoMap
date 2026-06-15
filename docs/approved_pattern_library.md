# Approved Pattern Library

Project: AutoMap: County GIS Request Engine

Version: v1.9

## Purpose

The approved pattern library stores reusable map-request patterns from local approved packets. Patterns help AutoMap suggest defaults and explain likely layer choices for future requests.

Patterns are review aids. They do not replace the verified layer catalog and do not create maps automatically without review.

## Tables

AutoMap safely creates these additive tables in the `automap` schema:

```text
automap.approved_pattern_library
automap.clarification_defaults
automap.recipe_feedback_log
```

Tables are created with `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ADD COLUMN IF NOT EXISTS`. AutoMap does not drop or rewrite existing tables.

## Approved Pattern Records

An approved pattern can include:

- raw and normalized prompt
- primary and secondary intents
- geographies and topics
- selected layer keys
- rejected layer keys
- preferred and avoided layer keys
- spatial operations
- filter plan
- clarification answers
- reviewer notes
- accepted assumptions
- warning resolutions
- missing-data decisions
- final publish readiness

Only approved packets with `final_publish_ready=true` are accepted as approved patterns.

## Clarification Defaults

Clarification defaults are derived from approved clarification answers. Examples:

- `near schools = 0.5 miles`
- `flood scope = floodway + 100-year floodplain`
- `current development activity = mark missing`

These defaults are shown to reviewers as suggestions. Reviewers can accept or override them.

## Pattern Matching

AutoMap compares current requests to approved patterns using deterministic similarity signals:

- primary intent
- secondary intents
- topics
- geography
- prompt token overlap
- historical/current compatibility

Historical patterns do not override current requests. New verified OpenData layers continue to outrank old learned legacy preferences unless the request is explicitly historical.

## API

```text
GET /api/patterns
GET /api/patterns/{pattern_key}
POST /api/patterns/learn-from-approved
GET /api/clarification-defaults
```

## CLI

```bash
python -m app.main --learn-from-approved-packet outputs/review_packets_approved/<approved-packet-folder>
python -m app.main --list-patterns
python -m app.main --list-clarification-defaults
```

## Boundaries

The approved pattern library does not:

- call external LLM APIs
- train a model
- ingest full geometries
- download feature datasets
- publish ArcGIS items
- require ArcGIS login
- connect to CFS or `cfs_dev`
- expose secrets or `.env` values
