# AutoMap Interactive Clarification Loop

Project: AutoMap: County GIS Request Engine

Version: v1.8

## Purpose

The interactive clarification loop lets a GIS reviewer answer AutoMap's review questions before continuing with a draft map. It is designed for prompts that are understandable but ambiguous, such as requests that use words like "near", "recent", "commercial", "best sites", or "development pressure".

AutoMap stays deterministic and local. It does not call external LLM APIs, does not invent layers, does not ingest full geometries, and does not publish to ArcGIS.

## What Gets Clarified

AutoMap can ask typed questions for:

- distance thresholds, such as what should count as "near"
- recent time ranges, such as 1 year, 3 years, or 5 years
- flood layer scope, such as floodway, 100-year floodplain, 500-year floodplain, or all flood hazard layers
- commercial zoning assumptions
- missing data decisions, such as whether to mark current permits as missing or use a legacy fallback if one exists
- suitability priorities, such as road access, flood avoidance, zoning, parcel size, or development activity

Each question records its intent, related layer or filter when known, blocking level, options, default answer, and help text.

In v1.9, questions may also show a suggested default from approved local patterns. The reviewer can accept or override the suggestion. Suggestions are review aids only; they do not invent layers or bypass human review.

## Workflow

1. A user submits a prompt on `/map-request`.
2. AutoMap creates an initial recipe using the trusted layer catalog.
3. If clarification would improve the map, the frontend shows an `Answer Clarifying Questions` action.
4. The `/clarify` page opens a local clarification session.
5. The reviewer answers questions.
6. AutoMap builds a refined request context.
7. AutoMap regenerates request intelligence, the analysis plan, selected layers, filters, warnings, and the map recipe.
8. The recipe records the applied refinements and changes from the original recipe.
9. The user continues to `/recipe-review` with the refined recipe.

The original recipe is preserved for comparison. The refined recipe becomes the active workflow recipe only after the reviewer chooses to refine.

## Database Table

AutoMap safely creates the following table in its own schema:

```text
automap.clarification_sessions
```

The table stores:

- session id
- raw prompt
- initial recipe
- questions
- answers
- refined prompt
- refined request context
- refined recipe
- changes summary
- status
- timestamps

The table is created with additive SQL only. AutoMap does not drop or rewrite existing tables.

## API Routes

The FastAPI backend exposes local JSON routes:

```text
POST /api/clarification/start
GET /api/clarification/{session_id}
POST /api/clarification/{session_id}/answer
POST /api/clarification/{session_id}/refine
GET /api/clarification
```

Responses are sanitized and do not expose `.env` values, database URLs, ArcGIS credentials, or real publish actions.

## Example

Prompt:

```text
Show development pressure near schools and flood zones in Concord.
```

Likely questions:

- What distance should count as near? Example: 500 feet, 0.25 miles, 0.5 miles.
- Which flood hazard layers should be included?
- Current permit and planning case layers are not available in the verified catalog. How should AutoMap handle that missing data?

Example answers:

- near schools = 0.5 miles
- flood scope = floodway plus 100-year floodplain
- development activity = mark current data as missing

The refined recipe records:

- an explicit 0.5 mile proximity assumption
- selected floodway and 100-year floodplain layers
- 500-year floodplain removed if it was only part of the ambiguous initial flood scope
- current development activity recorded as missing data
- remaining review warnings, if any

## Safety Rules

AutoMap only uses verified catalog records when selecting layers. If a requested dataset is unavailable, AutoMap records missing data rather than inventing a source.

The clarification loop does not:

- connect to the CFS database
- inspect or modify `cfs_dev`
- ingest full geometries
- download full feature datasets
- require ArcGIS login
- publish real ArcGIS items
- expose real publish in the frontend
- use ports 3000 or 8000

CFS remains separate and untouched. AutoMap runs on frontend port `3010` and backend/API port `8010`.
