# Filter Planner

The filter planner turns selected catalog layers into a per-layer `filter_plan` for map recipes.

For each selected layer, the planner reports:

- candidate fields
- selected field
- sampled candidate values
- draft where clause when a safe one can be produced
- confidence score
- review status

## Behavior

- Geography filters look for real municipality, jurisdiction, district, area, or name fields.
- Zoning filters look for real zoning, district, code, and class fields.
- School filters look for school, district, attendance, elementary, middle, and high fields.
- Floodplain sublayers usually do not need an attribute filter because the selected layer already represents the flood condition.
- Recent time filters need review unless a date field and time range are confirmed.

The planner never invents field names or data sources. If field/value evidence is uncertain, it sets `needs_review`.

## Example

```bash
python -m app.main --validate-recipe "Show parcels in Concord that are in the 100-year floodplain."
```
