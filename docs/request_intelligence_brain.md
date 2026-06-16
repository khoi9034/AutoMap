# AutoMap Request Intelligence Brain

AutoMap's request intelligence brain is a deterministic interpretation layer for messy county GIS map requests. It does not call external LLM APIs, does not invent layers, and does not publish anything.

AutoMap v2.7 adds `scenario_context` to request intelligence. Growth, suitability, constraint, transportation-access, and development-pressure prompts can now recommend the Scenarios workflow before any bounded analysis is considered.

AutoMap v3.0 adds real parcel lookup support on top of parcel-context detection. Prompts with PINs, PIN14s, parcel IDs, address-like inputs, `my parcels`, or `these parcels` include a `parcel_context` section and recommend the Parcel Workspace for safe identifier matching, candidate review, and selected-parcel GeoJSON generation.

## Purpose

The request intelligence brain helps AutoMap explain what it understood before a human reviewer approves a draft. It enriches map recipes with:

- detected high-level intents
- confidence by intent
- primary and secondary intents
- extracted constraints and opportunities
- spatial relationships
- ambiguity flags
- clarifying questions
- a plain-language reasoning summary
- unsupported or missing request parts
- scenario context and recommended scenario workflow when a prompt is better handled as a planning framework
- parcel context and recommended parcel workspace when identifiers or addresses are detected
- an analysis plan with required layers, optional layers, spatial steps, attribute steps, assumptions, blockers, and review questions

## Deterministic Modules

- `app/intent_classifier.py` classifies requests into supported intents such as `property_lookup`, `flood_exposure`, `zoning_review`, `development_pressure`, `growth_suitability`, and `historical_comparison`.
- `app/spatial_intent_planner.py` converts request language into GIS operation steps such as intersect, proximity/buffer, geography clipping, overlay, exclusion of constraints, and suitability review.
- `app/clarifying_questions.py` generates reviewer questions for ambiguous terms such as near, recent, commercial, historical, and suitability.
- `app/request_quality_evaluator.py` scores how complete the interpretation is and identifies unsupported or missing parts.
- `app/request_explainer.py` adds plain-language reasoning for selected and rejected layers.
- `app/scenario_classifier.py` identifies suitability and planning scenario prompts.
- `app/request_intelligence.py` orchestrates the modules and returns the recipe-ready `request_intelligence` and `analysis_plan` objects.
- `app/parcel_input_parser.py` detects parcel IDs, PINs, PIN14s, address-like inputs, pasted parcel lists, and privacy-sensitive owner lookup requests.

## Safety Rules

AutoMap still uses only the verified layer catalog for layer selection. If a requested dataset is not available, such as current permits, active planning cases, or the current development pipeline, AutoMap reports missing data instead of hallucinating a source.

In v2.5, request intelligence also checks the data gap resolver for verified external source candidates. If an approved active source exists, AutoMap can use it from the trusted catalog. If only candidate, proxy, reference, limited-coverage, or unverified sources exist, AutoMap keeps the missing-data warning and adds `data_gap_resolution_context` so reviewers can see the candidate source, verification status, and limitations.

The request intelligence brain:

- does not ingest full geometries
- does not download full feature datasets
- does not create or publish ArcGIS items
- does not require ArcGIS login
- does not expose real publishing in the frontend
- does not use external paid LLM APIs
- does not connect to CFS or the `cfs_dev` database

## Example

Prompt:

```text
Show development pressure near schools and flood zones in Concord.
```

Expected interpretation:

- intents: `development_pressure`, `school_district_lookup`, `flood_exposure`
- spatial relationships: proximity near schools, overlay/intersect flood layers, clip/filter to Concord
- clarifying question: what distance should count as near?
- missing data: current development activity if no verified layer exists
- selected layers: only verified catalog layers such as flood hazards, school districts, and municipal boundaries

## Frontend Display

The Next.js frontend shows request intelligence on:

- `/map-request`
- `/recipe-review`

The panel displays intent badges, confidence scores, constraints, opportunities, ambiguity flags, unsupported parts, spatial relationships, assumptions, and review questions.

## CLI

Use the existing recipe command:

```bash
python -m app.main --make-recipe "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-recipe "Show development pressure near schools and flood zones in Concord."
python -m app.main --make-recipe "Make a planning map for commercial growth but avoid flood areas."
python -m app.main --make-recipe "Show current permits near Kannapolis."
```

The JSON output includes `request_intelligence` and `analysis_plan`.

When source candidates exist for missing data, the JSON also includes `data_gap_resolution_context`. Scenario-style prompts include `request_intelligence.scenario_context`. This is review context only and does not authorize proxy data as official permit, planning case, development approval, or suitability decision data.

Parcel-centered prompts include `request_intelligence.parcel_context` and recipe-level `parcel_context` metadata. Matching and local reports should be created through `/parcel-workspace` or the parcel CLI commands so AutoMap can preserve unmatched identifiers and avoid broad parcel downloads.
