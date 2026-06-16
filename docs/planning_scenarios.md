# Planning Scenarios

AutoMap v2.7 adds deterministic planning scenario workflows for growth, suitability, constraints, transportation access, development pressure, planning cases, school context, flood avoidance, and historical change. AutoMap v2.8 adds a local Scenario Workbench for weight tuning, variants, comparisons, and scenario-to-recipe conversion.

Scenarios are planning frameworks. They are not official recommendations, entitlement decisions, permit approvals, capacity findings, or public-facing scores.

## What A Scenario Produces

A scenario includes:

- scenario type and title
- planning goal
- selected trusted catalog layers
- positive factors
- negative factors
- transparent scoring framework
- assumptions
- review questions
- source coverage warnings
- missing official data
- execution status
- official-use disclaimer

For v2.7, execution status is normally `scoring_plan_only`. AutoMap does not execute countywide parcel scoring.

## Supported Scenario Types

- `commercial_growth_suitability`
- `residential_growth_suitability`
- `development_pressure`
- `constraint_exposure`
- `transportation_access`
- `planning_case_context`
- `flood_avoidance`
- `school_impact_context`
- `historical_change_context`
- `unsupported_scenario`

## CLI

```bash
python -m app.main --make-scenario "Map commercial growth opportunities near high traffic roads but avoid floodplain."
python -m app.main --make-scenario "Show development pressure near schools and flood zones in Concord."
python -m app.main --make-scenario "Find areas suitable for residential growth but avoid flood risk."
python -m app.main --list-scenarios
python -m app.main --generate-scenario-report <scenario_id>
python -m app.main --create-scenario-variant <scenario_id> --params-json '{""variant_name"":""Road access priority"",""weight_overrides"":{""aadt_high_traffic"":40}}'
python -m app.main --scenario-to-recipe <scenario_id> --variant-id <variant_id>
```

## API

```text
POST /api/scenarios
GET /api/scenarios
GET /api/scenarios/{scenario_id}
POST /api/scenarios/{scenario_id}/report
POST /api/scenarios/{scenario_id}/variants
POST /api/scenario-comparisons
POST /api/scenarios/{scenario_id}/to-recipe
```

Responses are sanitized and do not expose database URLs, ArcGIS credentials, `.env` values, secrets, or real publish actions.

## Frontend

The `/scenarios` page provides:

- scenario prompt input
- sample scenario cards
- scenario type and confidence
- scoring framework table
- source coverage warnings
- missing data
- review questions
- local report generation
- optional draft map recipe generation from the same prompt
- weight tuning and variant creation

The `/scenario-workbench` page provides a fuller workbench for selecting stored scenarios, comparing variants, and converting a reviewed variant into a recipe.

## Safety

AutoMap does not bulk-ingest datasets, does not download full countywide data, does not publish ArcGIS items, and does not require ArcGIS login. Proxy sources remain labeled as proxy/context only. Missing official data remains visible.

The CFS database is separate and remains untouched.
