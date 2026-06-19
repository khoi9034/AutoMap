# Parcel Workspace

AutoMap v3.0 adds a parcel-centered workspace for real parcel lookup and selected-parcel GIS review drafts. AutoMap v3.1 adds parcel-origin proximity actions for nearest-facility and route-draft review. AutoMap v3.2 adds guided workflow behavior so parcel previews are blocked until a parcel is actually matched. AutoMap v3.5 separates address origins from parcel/PIN inputs so address prompts do not show parcel-unmatched errors.

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

Address prompts such as `my address 793 bartram ave` are treated as address origins. AutoMap first searches verified address fields and then verified parcel/address crosswalk fields if available. It does not infer private ownership or guess a parcel from ambiguous address candidates.

## Safe Matching

Parcel matching uses the verified Tax Parcels layer from `automap.layer_catalog`.

AutoMap:

- infers real identifier fields from catalog metadata and field profiles
- stores reviewed role mappings in `automap.parcel_field_map`
- supports exact and normalized PIN/PIN14 matching
- uses verified Addresses fields for address candidates when available
- runs count and attribute queries with `returnGeometry=false`
- preserves unmatched identifiers
- marks multiple matches as `needs_review`
- does not download all parcels
- does not download countywide parcel geometry

Only after a parcel set is matched and under safety limits can AutoMap fetch selected parcel geometry. The default selected-geometry limit is 100 parcels, with a hard max of 250.

## Focused Preview Behavior

Parcel-centered recipes now include `can_focus_map`, `can_fetch_geometry`, `preview_status`, and `analysis_status`.

If the identifier is unmatched, AutoMap:

- keeps the draft recipe for review
- marks `can_focus_map=false`
- blocks parcel-focused preview and parcel analysis
- does not create selected parcel GeoJSON
- does not use the broad Tax Parcels extent as a fake selected parcel map
- asks the user to correct the parcel ID, PIN, or address

If the identifier is matched safely, AutoMap fetches only the matched parcel geometry, computes a buffered parcel extent, and focuses the preview on that extent.

If an address is unmatched, the normal composer says `Address not found`, not `Parcel not matched`, and blocks focused preview until the user corrects the address.

## CLI

```bash
python -m app.main --profile-parcel-fields
python -m app.main --parse-parcels "5528-12-3456, 5528-12-7890"
python -m app.main --match-parcels "5528-12-3456"
python -m app.main --create-parcel-set "5528-12-3456, 5528-12-7890"
python -m app.main --fetch-selected-parcels <parcel_set_id>
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

The page supports field profiling, parsing, matching, ambiguous candidate review, selected parcel GeoJSON fetch, context overlay selection, nearby distance review, parcel context recipe generation, and local parcel report exports.

The guided workflow page is:

```text
http://localhost:3010/workflow
```

It keeps prompt, recipe, preview, adjustment, analysis/report, and export actions together for normal local use.

The page also includes proximity actions for nearest school, nearest fire station, containing fire district, and route draft to address. These actions use the current parcel/PIN/address input as the origin and route through the same bounded v3.1 proximity workflow.

## Safety

Parcel workspace outputs are draft review artifacts. They do not publish to ArcGIS, require ArcGIS login, bulk-ingest parcels, or use the protected external planning database. Current permits remain unresolved unless an official verified source is added.

Route drafts are straight-line references only unless an approved routing/network service is added later.
