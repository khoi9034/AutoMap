# Parcel Workspace

AutoMap v2.9 adds a parcel-centered workspace for GIS review drafts.

The workspace accepts:

- parcel IDs
- PIN values
- PIN14 values
- address-like inputs
- comma-separated parcel lists
- newline-separated parcel lists
- CSV-style pasted parcel lists
- prompts such as `my parcels` or `these parcels`

Owner-name searches are not assumed. If a user asks for owner lookup, AutoMap marks the request as privacy-sensitive and needs review. It only uses verified public parcel fields when a reviewer confirms the field and purpose.

## Safe Matching

Parcel matching uses the verified Tax Parcels layer from `automap.layer_catalog`.

AutoMap:

- infers real identifier fields from catalog metadata and field profiles
- runs count and attribute queries with `returnGeometry=false`
- preserves unmatched identifiers
- marks multiple matches as `needs_review`
- does not download all parcels
- does not download countywide parcel geometry

Only after a parcel set is matched and under safety limits should later analysis request selected parcel geometry.

## CLI

```bash
python -m app.main --parse-parcels "5528-12-3456, 5528-12-7890"
python -m app.main --create-parcel-set "5528-12-3456, 5528-12-7890"
python -m app.main --parcel-context "Make a map of parcel 5528-12-3456 and show zoning, floodplain, schools, and roads."
python -m app.main --list-parcel-sets
python -m app.main --get-parcel-set <parcel_set_id>
python -m app.main --generate-parcel-report <parcel_set_id>
```

## Frontend

Open:

```text
http://localhost:3010/parcel-workspace
```

The page supports parsing, parcel-set creation, context overlay selection, nearby distance review, parcel context recipe generation, and local parcel report exports.

## Safety

Parcel workspace outputs are draft review artifacts. They do not publish to ArcGIS, require ArcGIS login, bulk-ingest parcels, or use the protected external planning database.
