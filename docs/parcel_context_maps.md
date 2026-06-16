# Parcel Context Maps

Parcel context maps focus a draft map recipe around a matched parcel set instead of a broad geography.

## Supported Context Layers

Core context:

- Tax Parcels
- Addresses
- Municipal District
- ETJ Boundary
- Zoning
- Zoning by municipality when applicable

Constraints:

- FloodWay
- FloodPlain100year
- FloodPlain500year
- Hydrology
- School Districts

Transportation:

- streets / centerlines
- AADT traffic counts
- STIP projects

Development and activity:

- Accela / plan-review proxy if verified
- Concord planning cases when the geography is Concord
- current permit gap notes when official current permits remain unresolved
- current planning case gap notes outside limited Concord coverage

## Recipe Output

Parcel-centered recipes include:

```json
{
  "parcel_context": {
    "parcel_set_id": "parcel_set_example",
    "input_type": "pin",
    "parsed_identifiers": [],
    "matched_count": 1,
    "unmatched_identifiers": [],
    "matched_parcels_summary": [],
    "parcel_extent": {},
    "context_layers": [],
    "nearby_distance": "0.25 miles",
    "parcel_warnings": []
  }
}
```

The recipe also preserves `source_coverage`, `missing_data_needed`, proxy warnings, limited coverage warnings, and draft-only review reasons.

## Reports

Parcel reports are written under:

```text
outputs/parcel_reports/
```

Each report folder includes:

- `parcel_context_report.html`
- `parcel_context_report.md`
- `parcel_context_report.json`
- `parcel_layer_summary.csv`
- `parcel_warnings.json`
- `export_manifest.json`

Generated reports are local review exports and are ignored by Git.

## Boundaries

AutoMap does not treat proxy development sources as official approvals, does not invent owner data, does not silently resolve current permit gaps, and does not execute countywide parcel analysis from the parcel workspace.
