# AutoMap Feedback Learning

Project: AutoMap: County GIS Request Engine

Version: v1.9

## Purpose

AutoMap feedback learning records local reviewer decisions so future requests can show reviewable defaults. This is not machine learning and does not call an external AI API. It is a deterministic approved-pattern memory system.

Feedback can come from:

- approved packets
- clarification sessions
- adjusted packets
- direct recipe feedback

## What AutoMap Learns

From approved local workflows, AutoMap can remember:

- selected layer keys
- rejected or avoided layer keys
- reviewer-approved clarification answers
- common distance defaults
- flood scope choices
- accepted assumptions
- warning resolutions
- missing-data decisions
- reviewer notes

For example, if approved development-pressure requests repeatedly use `0.5 miles` for "near schools", AutoMap can suggest that value on a similar future clarification question.

## What AutoMap Does Not Learn

AutoMap does not train a model, infer private data, ingest geometries, publish ArcGIS items, or invent new layers. If a layer is missing from the verified catalog, AutoMap records it as missing data instead of hallucinating a source.

## Feedback Log

Feedback rows are stored locally in:

```text
automap.recipe_feedback_log
```

Supported feedback types:

- `approved`
- `needs_changes`
- `rejected`
- `manual_adjustment`
- `clarification_answered`

## API

```text
POST /api/feedback/recipe
POST /api/clarification/{session_id}/learn
```

Responses are sanitized and do not expose secrets, database URLs, ArcGIS credentials, or real publish controls.

## Safety

Feedback learning stays inside AutoMap's own database and schema. It does not connect to the CFS database, does not touch `cfs_dev`, and does not use ports 3000 or 8000.
