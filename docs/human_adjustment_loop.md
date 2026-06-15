# Human Adjustment Loop

AutoMap v0.6 lets a human reviewer adjust a draft review packet before any future publishing step.

AutoMap drafts are not final maps. The adjustment loop gives GIS staff a local, auditable way to refine the draft recipe and WebMap JSON after reviewing selected layers, filters, warnings, and missing data.

## What Can Be Adjusted

Adjustment files can be YAML or JSON. YAML is recommended for human editing.

Supported fields:

- `map_title`
- `map_description`
- `suggested_extent_override`
- `layer_order`
- `layer_adjustments`
- `definition_expression_overrides`
- `symbology_overrides`
- `popup_overrides`
- `reviewer_notes`
- `warnings_to_resolve`
- `warnings_to_keep`
- `missing_data_notes`
- `publish_ready`

Layer adjustments can change visibility, opacity, title, role, legend display, or remove a layer from the adjusted draft.

## Workflow

1. Create a review packet:

```bash
python -m app.main --make-review-packet "Show parcels in Concord that are in the 100-year floodplain."
```

2. Create an editable adjustment template:

```bash
python -m app.main --create-adjustment-template outputs/review_packets/<packet-folder>
```

3. Edit `adjustments.template.yaml`.

4. Apply the adjustments:

```bash
python -m app.main --apply-adjustments outputs/review_packets/<packet-folder> outputs/review_packets/<packet-folder>/adjustments.template.yaml
```

5. Validate the adjusted packet:

```bash
python -m app.main --validate-adjusted-packet outputs/review_packets_adjusted/<adjusted-packet-folder>
```

## Output

AutoMap never modifies the original review packet in place. Adjusted packets are written to:

```text
outputs/review_packets_adjusted/
```

Each adjusted packet includes:

- `original_recipe.json`
- `original_webmap.json`
- `adjusted_recipe.json`
- `adjusted_webmap.json`
- `applied_adjustments.json`
- `adjusted_review_summary.md`
- `adjusted_warnings.json`
- `adjusted_layer_review.json`
- `adjusted_review.html`

## Warning Review

Warnings listed in `warnings_to_resolve` are marked as `reviewer_resolved`. They are not deleted. AutoMap preserves an audit trail in `adjusted_warnings.json` and `applied_adjustments.json`.

Warnings listed in `warnings_to_keep` remain active.

If `publish_ready` is set to `true` while active warnings or publishing blockers remain, AutoMap changes it back to `false` and records:

```text
Publishing blocked because unresolved warnings remain.
```

## Publishing Boundary

`publish_ready` is only a human review flag. It does not publish anything. AutoMap v0.6 does not create ArcGIS Online, Enterprise, or Portal items and does not require ArcGIS login.

AutoMap does not ingest full geometries or download full feature datasets during the adjustment workflow.

## Project Boundary

AutoMap uses its own local database and schema. The CFS database is separate and must not be touched by this workflow.
