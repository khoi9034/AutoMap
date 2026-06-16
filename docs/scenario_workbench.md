# Scenario Workbench

AutoMap v2.8 adds a local Scenario Workbench for tuning planning scenario assumptions before a scenario moves into the recipe/review workflow.

The workbench is for staff review. It does not publish, does not execute geometry scoring, does not require ArcGIS login, and does not turn suitability scores into official recommendations.

## What It Supports

- create scenario variants from stored planning scenarios
- override factor weights
- enable or disable factors
- add reviewer assumptions
- normalize reviewer weights for display
- compare scenarios and variants
- convert a scenario or variant into a draft map recipe

## CLI

```bash
python -m app.main --create-scenario-variant <scenario_id> --params-json '{""variant_name"":""Road access priority"",""weight_overrides"":{""aadt_high_traffic"":40,""floodplain_avoidance"":-30}}'
python -m app.main --list-scenario-variants
python -m app.main --compare-scenarios --scenario-ids "<scenario_id>" --variant-ids "<variant_id>"
python -m app.main --scenario-to-recipe <scenario_id>
python -m app.main --scenario-to-recipe <scenario_id> --variant-id <variant_id>
```

## API

```text
POST /api/scenarios/{scenario_id}/variants
GET /api/scenarios/{scenario_id}/variants
GET /api/scenario-variants/{variant_id}
POST /api/scenario-comparisons
POST /api/scenarios/{scenario_id}/to-recipe
POST /api/scenario-variants/{variant_id}/to-recipe
```

Responses are JSON and are sanitized. They do not expose database URLs, ArcGIS credentials, `.env` values, or real publish actions.

## Frontend

Use:

```text
http://localhost:3010/scenario-workbench
```

The page lets reviewers open an existing scenario, tune weights, save a variant, compare variants, and convert a scenario or variant into a draft map recipe.

## Safety

- Scenario scores are planning-support drafts, not official recommendations.
- Proxy and reference sources remain context only unless reviewed.
- Missing official permit data remains unresolved.
- No full countywide datasets are downloaded.
- No geometry scoring runs unless a separate bounded analysis passes safety checks.
- CFS is separate and remains untouched.
