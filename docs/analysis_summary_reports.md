# Analysis Summary Reports

AutoMap v2.3 converts safe analysis runs and refinement sessions into local summary analytics report packages.

These reports are draft GIS review artifacts. They are not official maps, do not publish to ArcGIS, do not require ArcGIS login, and do not create hosted layers.

## Purpose

Analysis reports help GIS and planning reviewers understand what AutoMap counted, why a run was blocked or completed, which layers were involved, and what safer refinements are available.

Reports can be generated from:

- analysis runs
- blocked analysis runs
- summary-only refinement sessions
- other refinement sessions when available

## Count And Statistics Only

v2.3 reports are built from analysis receipts and safe ArcGIS REST summary calls.

Where supported, AutoMap tries grouped summaries with:

- `returnGeometry=false`
- count/statistics queries only
- real fields from the layer catalog and field profiles
- no invented fields

If a layer does not support statistics or the field is not suitable, AutoMap records the grouped summary as unsupported and still writes the report.

Summary-only refinement reports do not download parcel geometry and do not create GeoJSON.

## Report Files

Reports are written under:

```text
outputs/analysis_reports/<timestamp>_<map_title_slug>/
```

Each package includes:

- `analysis_report.html`
- `analysis_report.md`
- `analysis_report.json`
- `summary_tables.json`
- `layer_summary.csv`
- `warning_summary.json`
- `export_manifest.json`

PDF export is intentionally skipped in v2.3 until a reliable local PDF path is added.

## CLI

```bash
python -m app.main --generate-analysis-report <analysis_run_id>
python -m app.main --generate-analysis-report-from-refinement <refinement_session_id>
python -m app.main --list-analysis-reports
python -m app.main --validate-analysis-report outputs/analysis_reports/<report-folder>
```

Validation checks required files, draft-only disclaimer text, protected markers, secrets, database URLs, ArcGIS credentials, and protected database references.

## API

```text
POST /api/analysis/reports
POST /api/analysis/reports/from-refinement
GET /api/analysis/reports
GET /api/analysis/reports/{report_id}
```

API responses are sanitized JSON. They do not expose `.env` values, database URLs, ArcGIS credentials, or real publish actions.

## Frontend

The Next.js frontend includes:

```text
/analysis-reports
```

The page lists recent analysis runs, refinement sessions, and generated reports. It can generate local report packages and preview report summaries with links to the HTML, Markdown, JSON, and CSV artifacts.

The `/analysis` page also shows a `Generate Analysis Report` action after a refinement result is available.

## Safety

AutoMap v2.3 does not:

- bulk-ingest countywide datasets
- download parcel geometry for summary-only reports
- raise feature limits to force execution
- publish reports or derived layers
- upload results to ArcGIS Online, Enterprise, or Portal
- require ArcGIS login
- touch external project databases

Generated analysis reports are local files and are ignored by Git.

The CFS database remains separate and untouched.
