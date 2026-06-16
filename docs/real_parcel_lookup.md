# Real Parcel Lookup

AutoMap v3.0 matches parcel-centered inputs against verified Tax Parcels and Addresses metadata.

## What AutoMap Uses

- `automap.layer_catalog` for verified Tax Parcels and Addresses layers
- `automap.layer_field_profile` for real field names and aliases
- `automap.parcel_field_map` for reviewed field-role mappings

AutoMap never assumes parcel, address, or owner fields. If field profiles are missing, the parcel field mapper profiles the trusted layers first and stores role mappings such as `pin`, `pin14`, `parcel_id`, `address`, and `object_id`.

## Matching Rules

- PIN/PIN14 matching supports exact values and normalized values with hyphens/spaces removed.
- Address matching uses verified address fields and returns candidates when ambiguous.
- Matching starts with `returnGeometry=false`.
- Geometry is fetched only after matched parcel count is safely bounded.
- Owner-name lookup is not performed by default.

## Commands

```bash
python -m app.main --profile-parcel-fields
python -m app.main --match-parcels "5528-12-3456"
python -m app.main --fetch-selected-parcels <parcel_set_id>
```

Fake or invalid identifiers should return `unmatched` or `needs_review` without broad parcel downloads.

## Safety

AutoMap does not bulk-ingest parcels, download countywide parcels, publish ArcGIS items, or require ArcGIS login. Current permit data remains unresolved unless an official verified current permit source is added.
