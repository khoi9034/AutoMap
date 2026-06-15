# AutoMap Report and Export Center

AutoMap v1.7 turns local workflow packets into shareable report packages for GIS review.

## Purpose

Reports summarize the AutoMap draft workflow without publishing anything. They are useful for staff review, handoff, QA, and portfolio/demo documentation.

Reports can be generated from:

- review packets
- adjusted packets
- approved packets
- dry-run publish receipts
- portal smoke-test dry-run receipts

## Supported Outputs

Each report folder is written under:

```text
outputs/reports/<timestamp>_<map_title_slug>/
```

Generated files:

- `report_summary.md`
- `report_summary.html`
- `report_data.json`
- `layer_table.csv`
- `warning_report.json`
- `export_manifest.json`

PDF export is not enabled in v1.7. HTML and Markdown are the supported readable report formats, with JSON and CSV available for structured review.

## Report Content

Reports include:

- original prompt
- generated map title
- workflow status
- selected layers and layer roles
- layer URLs and source status
- definition expressions
- spatial operations
- symbology notes
- grouped warnings
- missing data and data gaps
- adjustment notes when available
- approval decision and `final_publish_ready` when available
- dry-run publish receipt when available
- portal smoke-test dry-run receipt when available
- draft-only disclaimer
- statement that CFS was not accessed or modified

## CLI

```bash
python -m app.main --generate-report outputs/review_packets/<packet-folder>
python -m app.main --generate-report outputs/review_packets_adjusted/<adjusted-packet-folder>
python -m app.main --generate-report outputs/review_packets_approved/<approved-packet-folder>
python -m app.main --list-reports
python -m app.main --validate-report outputs/reports/<report-folder>
```

## API

The frontend uses JSON-only API routes:

```text
POST /api/generate-report
GET /api/reports
GET /api/reports/{report_id}
```

API responses are sanitized. They do not expose database URLs, ArcGIS credentials, `.env` values, secrets, or real publish actions.

## Frontend

The Next.js frontend adds:

- `/reports`
- `frontend/components/report-card.tsx`
- `frontend/components/report-preview.tsx`
- `frontend/components/report-center-client.tsx`

The Report Center lists recent review, adjusted, and approved packets, can generate a local report package, and shows links to generated report files.

## Safety Boundary

Reports are local exports for review. They are not official maps, do not publish to ArcGIS, do not require ArcGIS login, do not ingest geometries, and do not create or share ArcGIS items.

Generated reports live under `outputs/`, which is ignored by Git. Do not commit generated report packages.

CFS uses a separate repository and database and must remain untouched by AutoMap report generation.
