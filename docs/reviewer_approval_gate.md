# Reviewer Approval Gate

AutoMap v1.1 adds a formal local sign-off step between an adjusted packet and any future publishing workflow.

The approval gate is still local-only. It does not publish to ArcGIS Online, Enterprise, or Portal, does not require ArcGIS login, and does not create ArcGIS items. It only creates an approved packet and an audit receipt when a reviewer has addressed warnings, blockers, and missing data.

## Workflow

1. Create or locate an adjusted packet:

```bash
python -m app.main --make-review-packet "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --create-adjustment-template outputs/review_packets/<packet-folder>
python -m app.main --apply-adjustments outputs/review_packets/<packet-folder> outputs/adjustment_templates/<packet-folder>_adjustments.template.yaml
```

2. Create an approval template:

```bash
python -m app.main --create-approval-template outputs/review_packets_adjusted/<adjusted-packet-folder>
```

3. Edit the YAML approval file under `outputs/approval_templates/`.

4. Apply the approval:

```bash
python -m app.main --apply-approval outputs/review_packets_adjusted/<adjusted-packet-folder> outputs/approval_templates/<adjusted-packet-folder>_approval.template.yaml
```

5. Validate the approved packet:

```bash
python -m app.main --validate-approved-packet outputs/review_packets_approved/<approved-packet-folder>
```

6. Dry-run publish only after `final_publish_ready = true`:

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
```

In v1.2, real private draft publishing is possible from approved packets only, but it remains CLI-only and blocked unless all explicit environment safeguards are enabled.

## Approval File

Approval files can be YAML or JSON. YAML is preferred for local human review.

Supported fields:

- `reviewer_name`
- `reviewer_role`
- `decision`: `approved`, `needs_changes`, or `rejected`
- `reviewer_notes`
- `warning_resolutions`
- `accepted_risks`
- `missing_data_decisions`
- `publish_ready_requested`

Warning resolution actions:

- `resolved`: reviewer considers the warning closed.
- `accepted`: reviewer accepts the warning or limitation for local draft readiness.
- `keep`: warning remains visible but is documented as non-blocking with a reviewer note.

Missing-data decisions must explicitly address each item in `missing_data_needed` when missing data remains.

## Publish-Ready Rules

`final_publish_ready` can be true only when:

- the decision is `approved`
- `publish_ready_requested` is true
- `adjusted_recipe.json`, `adjusted_webmap.json`, and `applied_adjustments.json` exist
- every active warning or blocker is resolved, accepted, or kept with a reviewer note
- every missing-data item has a reviewer decision
- the approved WebMap still has valid operational layer URLs

If the reviewer chooses `needs_changes` or `rejected`, the approved packet can still be written for audit, but `final_publish_ready` remains false.

## Output

Approval never mutates the adjusted packet in place. AutoMap writes a separate folder:

```text
outputs/review_packets_approved/<adjusted-packet-name>_approved_<timestamp>/
```

Each approved packet includes:

- `approved_recipe.json`
- `approved_webmap.json`
- `approval_file.json`
- `approval_receipt.json`
- `approved_warnings.json`
- `approved_layer_review.json`
- `approved_review_summary.md`
- `approved_review.html`

The receipt records reviewer identity, decision, block reasons, warning decisions, missing-data decisions, accepted risks, local-only approval status, no ArcGIS item creation, and the protected project database boundary.

## Local UI

Start the UI:

```bash
python -m app.main --serve-ui --ui-port 8010
```

The normal Next.js UI does not expose the approval page. Approval remains available through CLI/internal tooling, and the visible Map Composer flow keeps approval and publishing concepts out of normal map drafting.

## Approval History

AutoMap safely creates or updates:

```text
automap.review_approval_history
```

The table stores local audit rows for reviewer decision, final publish-ready status, block reasons, notes, and the approval receipt. It uses `CREATE TABLE IF NOT EXISTS` and additive columns only.

## Boundaries

- Approval is local-only and not official map approval.
- `publish_ready` means reviewer-approved for a future private draft publishing check.
- The approval gate itself does not publish to Portal.
- v1.2 real private draft publishing remains separately guarded by `--confirm-publish` and local environment flags.
- AutoMap does not ingest geometries or download full feature datasets.
- AutoMap does not use an external LLM API.
- AutoMap uses its own database and schema; the CFS database `cfs_dev` must not be touched.
