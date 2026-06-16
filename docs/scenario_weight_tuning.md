# Scenario Weight Tuning

Scenario weight tuning is a transparent reviewer workflow for adjusting draft planning factors.

Weights are not model outputs. They are reviewable assumptions used to explain how a scenario framework might prioritize opportunity, constraint, context, and proxy factors.

## Factor Controls

Each factor can include:

- `suggested_weight`
- `reviewer_weight`
- `enabled`
- `direction`
- `reviewer_note`
- `needs_review`
- normalized display weight

Total weights do not need to equal 100. AutoMap calculates normalized display percentages from enabled reviewer weights so reviewers can compare relative emphasis.

## Defaults

- Opportunity factors can receive positive reviewer weights.
- Constraint factors can receive penalty weights.
- Proxy/reference factors default to context-only.
- Missing official data is never scored as if it were present.
- Flood constraints remain penalty/constraint factors unless a reviewer explicitly changes the assumption.
- AADT can support high-traffic opportunity logic when the scenario calls for it.
- STIP remains planned transportation context.

## Variant Safety

Each variant records:

- changed weights
- disabled factors
- reviewer assumptions
- safety warnings
- proxy warnings
- missing official data warnings
- official-use disclaimer

If a reviewer gives a proxy/reference factor a non-zero weight, AutoMap keeps the variant reviewable and adds a warning. If a missing official data factor is given a positive score, AutoMap prevents it from becoming an opportunity score.

## Scenario To Recipe

Scenario-to-recipe conversion preserves:

- selected scenario layers
- source coverage warnings
- scoring framework or variant weights
- missing official data
- review questions
- official-use disclaimer

It does not publish, does not create ArcGIS items, and does not execute suitability scoring.

The CFS database is separate and remains untouched.
