# Field Intelligence

AutoMap v0.3 profiles fields from verified ArcGIS REST layer metadata so map recipes can name real fields instead of guessing.

## What It Stores

Field intelligence is stored in AutoMap's own PostGIS schema:

- `automap.layer_field_profile`
- `automap.layer_value_profile`
- `automap.recipe_validation_log`

Field profiles include field names, aliases, types, domains, and inferred roles such as date, geography, zoning, permit, status, school, and address candidates.

Value profiles store small samples from ArcGIS REST query endpoints. These checks always use `returnGeometry=false`, prefer distinct values, and fall back to a small non-geometry sample if distinct queries fail.

## Boundaries

- No full geometries are downloaded.
- No full feature datasets are ingested.
- Samples are metadata and small value checks only.
- CFS is separate and was not touched.
- AutoMap still does not generate ArcGIS web maps.

## Commands

```bash
python -m app.main --profile-layer-fields --layer-key cabarrus_new_cabarrus_county_zoning_0_cabarrus_county_zoning
python -m app.main --profile-catalog-fields
python -m app.main --profile-catalog-fields --category zoning
```
