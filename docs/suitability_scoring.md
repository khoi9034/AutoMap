# Suitability Scoring

AutoMap v2.7 suitability scoring is transparent and reviewable. It is not a model, not an official recommendation, and not an automated planning decision.

## Scoring Framework

Each factor records:

- `factor_key`
- `factor_label`
- `factor_type`
- `layer_keys`
- `suggested_weight`
- `direction`
- `scoring_method`
- `needs_review`
- `notes`

Factor types:

- `opportunity`
- `constraint`
- `context`
- `proxy`

Directions:

- `higher_is_better`
- `lower_is_better`
- `presence_is_good`
- `presence_is_bad`
- `reference_only`

Methods:

- `attribute_score`
- `proximity_score`
- `intersection_penalty`
- `reference_context`
- `not_executable_yet`

## Default Templates

Commercial growth suitability:

- positive: commercial/general business zoning, high AADT, road access
- context: STIP planned transportation projects
- negative: floodway and floodplain exposure, missing official current permit data
- proxy: Accela or plan-review activity

Residential growth suitability:

- positive: residential zoning, road access, parcels outside flood hazard
- context: school districts, development activity proxy
- negative: floodway/floodplain exposure, missing official current permit data

Development pressure:

- context/proxy: Accela or plan-review activity, planning cases where available, AADT/corridors, zoning, parcels
- limitation: proxy data does not equal approval, and current permits remain unresolved unless verified

Constraint exposure:

- constraints: floodway, 100-year floodplain, 500-year floodplain, school districts, hydrology where available, zoning limitations

## Execution Rules

v2.7 generates `scoring_plan_only` by default.

AutoMap does not:

- execute countywide parcel scoring
- raise safety limits to force execution
- download full feature datasets
- treat proxy sources as official approvals
- treat suitability scores as official planning decisions

If a reviewer wants execution, the request must go through the existing bounded analysis planner. Large jobs remain blocked and can use analysis refinement.

## Review Questions

Scenario output asks reviewers to confirm:

- weights
- commercial or residential zoning codes
- AADT thresholds
- road distance thresholds
- flood avoidance scope
- whether school context should be included
- whether a scenario should remain plan-only or move to bounded analysis

## Source Coverage

Suitability scoring uses the v2.6 source coverage model. AADT and STIP are transportation context. Accela and plan-review activity are proxy/context. Concord planning cases are limited coverage. Missing official current permits remain visible.

The CFS database is separate and remains untouched.
