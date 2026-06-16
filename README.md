# AutoMap: County GIS Request Engine

AutoMap converts plain-English county GIS map requests into structured map recipes using only approved GIS layers from a local layer catalog.

Version: `2.4.0`

## Current Phase

v2.4 Data Gap Resolver and External Source Connectors on top of analysis summary reporting and user-guided safe spatial analysis refinement.

This repository is intentionally independent. It does not connect to CFS or import CFS code. AutoMap uses its own local PostGIS database and trusted layer catalog.

## What AutoMap Does

AutoMap helps GIS and planning staff turn plain-English county map requests into draft review artifacts:

- prompt parsing and topic/geography detection
- verified ArcGIS REST layer matching
- field-aware filter planning
- structured map recipe JSON
- local ArcGIS WebMap JSON drafts
- review packets for human approval
- YAML-based human adjustment loop
- local reviewer approval gate
- live local browser map preview
- dry-run publish receipts
- guarded CLI-only private ArcGIS Web Map publishing from approved packets
- one-item private Portal smoke-test verification
- Next.js frontend workflow shell backed by FastAPI JSON APIs
- persistent end-to-end frontend workflow state
- local request history and system status
- local report/export packages for GIS review
- deterministic request intelligence with intent classification, spatial planning, clarifying questions, and layer-selection explanations
- interactive clarification sessions that refine recipes from reviewer answers
- deterministic feedback learning from approved packets, clarification answers, and reviewer decisions
- safe bounded spatial analysis execution with server-side query optimization and local GeoJSON outputs
- user-guided refinement for blocked spatial analyses, including summary-only outputs without geometry download
- summary analytics reports from analysis runs and refinements using counts/statistics instead of geometry download
- external source registry and data gap resolver for current permits, planning cases, development pipeline proxies, AADT, and STIP context

## What AutoMap Does Not Do Yet

AutoMap does not bulk-ingest full feature datasets, does not publish from the local UI, does not publish publicly, does not share to the organization, does not train models, and does not use an external LLM API.

ArcGIS publishing and smoke testing remain dry-run by default unless a guarded CLI path is explicitly confirmed with an approved packet and local environment safety flags. The frontend exposes dry-run actions only.

## Version Roadmap

1. Prompt-to-map-recipe engine
2. Semantic layer catalog
3. PostGIS connection
4. ArcGIS REST layer inspection
5. ArcGIS web map generator
6. Human review/edit loop
7. PDF/export tools
8. Local UI and preview
9. v1.0 demo polish and QA hardening
10. v1.1 reviewer approval gate
11. v1.2 controlled private ArcGIS publish
12. v1.3 portal publish smoke test and item verification
13. v1.4 Next.js frontend app shell
14. v1.5 end-to-end frontend workflow wiring
15. v1.6 frontend UX polish and map preview upgrade
16. v1.7 report and export center
17. v1.7 request intelligence brain
18. v1.8 interactive clarification loop
19. v1.9 feedback learning and approved pattern library
20. v2.0 safe spatial analysis execution
21. v2.1 bounded spatial query optimizer
22. v2.2 user-guided analysis refinement
23. v2.3 summary analytics and report export for analysis results
24. v2.4 data gap resolver and external source connectors

## Project Structure

```text
automaps/
  app/
    __init__.py
    main.py
    recipe_engine.py
    layer_matcher.py
    prompt_parser.py
    confidence.py
  data/
    layer_catalog.example.json
    test_prompts.json
  frontend/
    app/
    components/
    lib/
    types/
  outputs/
    sample_recipes/
  tests/
    test_prompt_parser.py
    test_layer_matcher.py
    test_recipe_engine.py
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## Local Setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m pytest
```

## Next.js Frontend

AutoMap v2.4 adds a data gap resolver and external source connector registry to the safe Analysis workflow in the Next.js + TypeScript shell under `frontend/`. The FastAPI backend remains the API and workflow engine, and the existing FastAPI/Jinja UI is preserved.

Start the backend API on port `8010`:

```bash
python -m app.main --serve-ui --ui-port 8010
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3010
```

Backend API:

```text
http://127.0.0.1:8010
```

`frontend/.env.example` contains:

```text
NEXT_PUBLIC_AUTOMAP_API_BASE_URL=http://127.0.0.1:8010
```

Do not commit `frontend/.env.local` or `frontend/node_modules/`.

AutoMap must not use the CFS reserved ports:

- CFS frontend: `http://localhost:3000`
- CFS backend: `http://127.0.0.1:8000`

Frontend pages:

- `/dashboard`
- `/map-request`
- `/clarify`
- `/recipe-review`
- `/map-preview`
- `/analysis`
- `/analysis-reports`
- `/adjustments`
- `/approval`
- `/publish-center`
- `/learning`
- `/reports`
- `/layer-catalog`
- `/data-gaps`
- `/external-sources`
- `/history`
- `/system-status`

The frontend can run dry-run publish and portal smoke-test dry-run actions only. Real publish remains CLI-only.

The workflow shell includes an operations dashboard, quick prompt bar, demo scenarios, clarification form, recipe review workspace, local map preview, layer panel, grouped warning panel, human adjustment editor, approval gate, dry-run publish center, approved-pattern learning center, report/export center, catalog search, data gaps, external source review, history, and sanitized system status.

The Map Request and Recipe Review pages now show request intelligence details: detected intents, confidence by intent, spatial relationships, ambiguity flags, clarifying questions, unsupported parts, and the analysis plan. This is deterministic rule-based interpretation only; AutoMap does not call external LLM APIs.

The Clarify Request page turns those clarifying questions into an interactive local review loop. Staff can answer distance, flood-scope, missing-data, recent-time, and zoning-code questions, then AutoMap regenerates request intelligence, the analysis plan, selected layers, filters, warnings, and the map recipe. The original recipe remains available for comparison, and the refined recipe records what changed.

The Learning page stores approved local workflows as reviewable defaults. AutoMap can suggest common distances, flood-scope choices, preferred layers, accepted assumptions, and missing-data decisions from approved patterns. These learned suggestions are deterministic, local, and reviewable. They do not train a model, call external AI APIs, invent layers, or override the verified catalog.

The Analysis page plans and runs safe bounded local GIS analysis for supported operations. v2.1 optimizes parcel selection by geography/constraint intersection, such as parcels in Concord intersecting the 100-year floodplain. It counts first, uses server-side spatial filtering to collect parcel ObjectIDs before downloading parcel geometry, blocks oversized requests, writes local GeoJSON under `outputs/analysis/`, and marks derived outputs as local review results only.

v2.2 adds a Refine Analysis panel for blocked runs. If the optimized candidate count still exceeds the feature limit, AutoMap can create reviewer-selectable options such as summary only, split batches, narrower constraints, real-field attribute filters, smaller geography, and ObjectID-only export. Summary-only refinement writes local Markdown/JSON outputs under `outputs/analysis_refinements/` without downloading parcel geometry.

v2.3 adds an Analysis Reports page and CLI/API report export commands for analysis runs and refinement sessions. Reports are written under `outputs/analysis_reports/` and include:

- `analysis_report.html`
- `analysis_report.md`
- `analysis_report.json`
- `summary_tables.json`
- `layer_summary.csv`
- `warning_summary.json`
- `export_manifest.json`

These reports use analysis receipts plus safe ArcGIS REST count/statistics queries with `returnGeometry=false` where supported. If grouped statistics are unsupported by a layer, AutoMap records that limitation and still produces the report. No parcel geometry is downloaded for summary-only reports.

AutoMap persists the active local workflow in browser storage so staff can move from prompt to recipe review, preview, adjustments, approval, and dry-run publishing without losing context on refresh. The stored workflow state is sanitized and does not include secrets.

v1.6 improves the map preview page with a draft-only preview shell, packet selector, layer review panel, warning group panel, clearer empty/loading/error states, and explicit safety labels. The frontend preview uses the backend preview config and existing local preview route. It does not require ArcGIS login and does not publish.

v1.7 adds local report packages under `outputs/reports/`. Reports can be generated from review, adjusted, or approved packets and include:

- `report_summary.html`
- `report_summary.md`
- `report_data.json`
- `layer_table.csv`
- `warning_report.json`
- `export_manifest.json`

PDF export is not enabled in v1.7; HTML and Markdown are the supported readable report formats. Reports are local review exports only. They are not official maps and do not publish to ArcGIS.

## PostGIS Setup

AutoMap uses its own local dev database called `automap` and its own schema called `automap`. This is separate from CFS and should use separate credentials. CFS uses the separate `cfs_dev` database and must not be modified by AutoMap setup.

Create a local environment file from the template:

```bash
cp .env.example .env
```

Then edit `.env` so `DATABASE_URL` points to AutoMap's own PostGIS database:

```text
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_LOCAL_POSTGRES_PASSWORD@localhost:5433/automap
AUTOMAP_DB_SCHEMA=automap
POSTGRES_ADMIN_URL=postgresql+psycopg2://postgres:YOUR_LOCAL_POSTGRES_PASSWORD@localhost:5433/postgres
```

To check the configured database connection:

```bash
python -m app.main --check-db
```

The check connects only to the configured AutoMap database, enables PostGIS extensions if permissions allow, creates the `automap` schema if it does not already exist, creates the `automap.project_database_check` health table, and reports the active schema. It refuses the protected CFS database name `cfs_dev`. It does not ingest county data or create ArcGIS web maps.

## ArcGIS REST Catalog Inspector

AutoMap uses verified ArcGIS REST metadata from Cabarrus County OpenData services to build `automap.layer_catalog`. New separated OpenData services are preferred. The legacy monolithic OpenData service is retained as fallback and historical metadata.

No full geometries are ingested yet, and no ArcGIS web maps are created. CFS is separate and was not touched.

```bash
python -m app.main --inspect-rest-sources
python -m app.main --build-catalog-from-rest
python -m app.main --verify-layer-catalog
python -m app.main --search-layers flood
```

## Map Recipe Engine

AutoMap v0.2 creates structured map recipes from plain-English GIS requests using only verified records in `automap.layer_catalog`.

The v1.7 request intelligence brain improves recipe interpretation with deterministic intent classification, richer synonym handling, spatial operation planning, clarifying questions, and plain-language explanations for selected and rejected layers. AutoMap still never invents layer names, URLs, fields, or data sources. If a requested source is missing, such as current permits, active planning cases, or a current development pipeline layer, AutoMap records missing data and asks for review instead of hallucinating a source.

```bash
python -m app.main --make-recipe "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-recipe "Show development pressure near schools and flood zones in Concord."
python -m app.main --make-recipe "Make a planning map for commercial growth but avoid flood areas."
python -m app.main --make-recipe "Show current permits near Kannapolis."
python -m app.main --make-recipe "Map recent permits and planning cases near Kannapolis."
python -m app.main --make-recipe "Show school districts for parcels in Harrisburg."
python -m app.main --make-recipe "Show commercial zoning around Concord."
python -m app.main --make-recipe "Show 2014 parcels and zoning."
```

Recipe JSON now includes `request_intelligence` and `analysis_plan`. See `docs/request_intelligence_brain.md`.

Refined recipe JSON also includes a `clarification` section with the local session id, questions, answers, applied refinements, changes from the initial recipe, remaining questions, and unresolved blockers. See `docs/interactive_clarification_loop.md`.

Recipe JSON also includes `learned_context` when similar approved patterns exist. Learned context includes similar patterns, suggested defaults, preferred layers, avoided layers, learned assumptions, missing-data decisions, confidence, and a review note. See `docs/approved_pattern_library.md` and `docs/feedback_learning.md`.

```bash
python -m app.main --learn-from-approved-packet outputs/review_packets_approved/<approved-packet-folder>
python -m app.main --list-patterns
python -m app.main --list-clarification-defaults
```

Use `--save-recipe` with `--make-recipe` to write a local JSON recipe under `outputs/sample_recipes/`. Generated outputs are local artifacts and are not committed.

## Spatial Analysis Execution

AutoMap v2.3 can execute safe bounded local spatial analysis for selected common operations, guide reviewers through safe refinement when a count remains too high, and export summary analytics reports from the results. It does not bulk-ingest countywide datasets and does not publish derived outputs.

Fully supported:

- `filter_by_geography`
- `select_by_intersection`
- `attribute_filter_only`

Stubbed with review-needed blocking:

- `select_by_distance`
- `exclude_by_intersection`
- `summarize_by_boundary`

Example:

```bash
python -m app.main --plan-analysis "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --execute-analysis "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --list-analysis-runs
python -m app.main --validate-analysis-run <analysis-run-id-or-output-folder>
python -m app.main --create-analysis-refinement <blocked-analysis-run-id>
python -m app.main --list-analysis-refinements
python -m app.main --select-analysis-refinement <session-id> summary_only --params-json "{}"
python -m app.main --execute-analysis-refinement <session-id>
python -m app.main --generate-analysis-report <analysis-run-id>
python -m app.main --generate-analysis-report-from-refinement <refinement-session-id>
python -m app.main --list-analysis-reports
python -m app.main --validate-analysis-report outputs/analysis_reports/<report-folder>
```

Analysis outputs are local files under `outputs/analysis/`, which is ignored by Git. A successful bounded intersection writes `analysis_result.geojson`, `analysis_receipt.json`, `input_recipe.json`, and `analysis_summary.md`.

v2.1 improves parcel/flood intersection execution with a bounded spatial query optimizer. AutoMap narrows target parcel queries with server-side spatial filters, deduplicates ObjectIDs, and downloads parcel geometries only when the final candidate count is under the safety limit. If optimized candidates remain too high, AutoMap blocks and recommends narrower geography, flood type, parcel type, zoning, or acreage filters.

v2.2 turns those blocked cases into a local refinement workflow. Summary-only mode returns counts, chunk metadata, ObjectID counts when available, and review notes without geometry download. Split-batches mode creates a bounded plan and does not silently execute all batches. Attribute filters are suggested only from real target-layer fields or profiled fields.

v2.3 turns analysis runs and refinement sessions into local report packages under `outputs/analysis_reports/`. Reports include readable HTML/Markdown, JSON data, summary tables, layer CSV, warnings JSON, and a manifest. Grouped summaries use `returnGeometry=false` ArcGIS REST statistics where supported; unsupported statistics are recorded as report limitations.

See `docs/spatial_analysis_execution.md`, `docs/spatial_query_optimizer.md`, `docs/analysis_refinement.md`, `docs/analysis_summary_reports.md`, and `docs/analysis_safety_limits.md`.

## Field Intelligence And Filter Planning

AutoMap v0.3 profiles real ArcGIS REST fields and small non-geometry value samples so recipes can include executable filter plans. Sampling uses `returnGeometry=false`; AutoMap still does not ingest full geometries or generate ArcGIS web maps.

```bash
python -m app.main --profile-layer-fields --layer-key cabarrus_new_cabarrus_county_zoning_0_cabarrus_county_zoning
python -m app.main --profile-catalog-fields
python -m app.main --profile-catalog-fields --category zoning
python -m app.main --validate-recipe "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --list-data-gaps
```

## Data Gap Resolver And External Sources

AutoMap v2.4 adds a local external source registry for important missing-data needs:

- current permits
- current planning cases
- current development pipeline
- plan review / Accela pipeline signals
- AADT traffic counts
- STIP transportation projects

Sources are marked `approved`, `candidate`, or `needs_review`, and as `active`, `proxy`, `reference`, or `legacy`. Candidate and proxy sources can improve review context, but they do not silently resolve official permit, planning case, or development pipeline gaps.

```bash
python -m app.main --load-external-sources
python -m app.main --inspect-external-sources
python -m app.main --list-external-sources
python -m app.main --resolve-data-gaps
python -m app.main --gap-candidates current_permits
python -m app.main --gap-candidates current_planning_cases
python -m app.main --gap-candidates current_development_pipeline
```

The frontend Data Gaps page shows candidate sources and limitation badges. The External Sources page shows the local registry and metadata inspection status.

Metadata inspection uses REST metadata, fields, domains, counts, and non-geometry checks only. AutoMap does not download full feature datasets, does not bulk-ingest data, and does not treat proxy pipeline data as official development approval.

## ArcGIS WebMap Draft Generator

AutoMap v0.4 creates local ArcGIS WebMap JSON drafts from map recipes. Drafts use verified catalog layer URLs and v0.3 filter-plan definition expressions only. AutoMap does not publish to ArcGIS Online or Portal, does not require an ArcGIS login, and does not ingest full geometries.

```bash
python -m app.main --make-webmap-draft "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-webmap-draft "Show commercial zoning around Concord."
python -m app.main --make-webmap-draft "Show school districts for parcels in Harrisburg."
python -m app.main --make-webmap-draft "Show 2014 parcels and zoning."
python -m app.main --validate-webmap-draft outputs/webmaps/<generated-file>.json
```

Generated WebMap drafts are local files under `outputs/webmaps/`, which is ignored by Git.

## Draft Review Packets

AutoMap v0.5 creates human-reviewable local packets for draft map requests. Each packet includes the recipe JSON, draft WebMap JSON, warning report, layer review table, Markdown summary, and a simple `review.html` dashboard. Packets help GIS staff approve or adjust map drafts before any future publishing phase.

Packets are local only. Nothing is published to ArcGIS Online, Enterprise, or Portal, and no ArcGIS login is required.

```bash
python -m app.main --make-review-packet "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-review-packet "Show commercial zoning around Concord."
python -m app.main --make-review-packet "Map recent permits and planning cases near Kannapolis."
python -m app.main --make-review-packet "Show 2014 parcels and zoning."
python -m app.main --validate-review-packet outputs/review_packets/<packet-folder>
```

Generated review packets are local files under `outputs/review_packets/`, which is ignored by Git.

## Human Adjustment Loop

AutoMap v0.6 lets a reviewer edit a local YAML or JSON adjustment file to refine a draft before any future publishing phase. The original review packet is preserved, and AutoMap writes a separate adjusted packet under `outputs/review_packets_adjusted/`.

`publish_ready` is only a review flag. It does not publish anything, does not create ArcGIS items, and does not require ArcGIS login.

```bash
python -m app.main --make-review-packet "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --create-adjustment-template outputs/review_packets/<packet-folder>
python -m app.main --apply-adjustments outputs/review_packets/<packet-folder> outputs/adjustment_templates/<packet-folder>_adjustments.template.yaml
python -m app.main --validate-adjusted-packet outputs/review_packets_adjusted/<adjusted-packet-folder>
```

Adjusted packets include original and adjusted recipe/WebMap JSON, applied adjustment audit details, adjusted warning status, layer review, and `adjusted_review.html`.

## Reviewer Approval Gate

AutoMap v1.1 adds a formal local approval step for adjusted packets. Reviewers can create an approval YAML template, mark warnings as resolved or accepted, document missing-data decisions, and create a separate approved packet under `outputs/review_packets_approved/`.

Approval is local-only. `final_publish_ready = true` means the reviewer approved the packet for a future private draft publishing check; it is not official map approval and does not publish anything to ArcGIS Online, Enterprise, or Portal.

```bash
python -m app.main --create-approval-template outputs/review_packets_adjusted/<adjusted-packet-folder>
python -m app.main --apply-approval outputs/review_packets_adjusted/<adjusted-packet-folder> outputs/approval_templates/<adjusted-packet-folder>_approval.template.yaml
python -m app.main --validate-approved-packet outputs/review_packets_approved/<approved-packet-folder>
python -m app.main --list-approvals
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
```

The local UI includes an approval page:

```text
http://127.0.0.1:8010/approval
```

Only approved packets with `final_publish_ready = true` show the UI dry-run publish and smoke-test actions. Real Portal publishing is CLI-only.

## Controlled Private ArcGIS Publish

AutoMap v1.2 can create a private draft ArcGIS Web Map item from an approved packet. Dry-run remains the default. Real publish is CLI-only and requires all safety gates:

- approved packet with `final_publish_ready = true`
- `--confirm-publish`
- `AUTOMAP_ALLOW_REAL_PUBLISH=true`
- `AUTOMAP_PUBLISH_DRY_RUN=false`
- ArcGIS credentials configured locally
- target folder configured

Configure portal settings locally in `.env` only:

```text
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_USERNAME=your_username
ARCGIS_PASSWORD=your_password
ARCGIS_TARGET_FOLDER=AutoMap Drafts
ARCGIS_PUBLISH_ENV=dev
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```

`ARCGIS_PORTAL_URL` is configurable because the organization may move portals. Supported profiles are `dev`, `staging`, and `production`; production remains blocked unless the explicit real-publish safeguards are enabled.

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
```

AutoMap creates new private Web Map items only. It does not publish publicly, does not share to the organization, does not overwrite or delete existing items, does not publish layers, and does not create Experience Builder apps.

## Safe ArcGIS Draft Publisher

AutoMap can validate an approved packet and prepare a private ArcGIS Web Map draft. The default is dry-run only, which writes `publish_receipt.json` and does not connect to ArcGIS or create an item.

Real publishing requires the v1.2 CLI safety gates, and raw review packets or adjusted packets cannot be real-published. AutoMap does not publish publicly, does not share to the organization, and does not overwrite or delete existing ArcGIS items.

```bash
python -m app.main --portal-check
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
```

## Portal Publish Smoke Test

AutoMap v1.3 adds a guarded smoke test for one private Web Map draft item from an approved packet. Dry-run remains the default and writes `smoke_test_receipt.json` without connecting to ArcGIS.

Real smoke testing is CLI-only and requires `--confirm-publish`, `AUTOMAP_ALLOW_REAL_PUBLISH=true`, `AUTOMAP_PUBLISH_DRY_RUN=false`, configured Portal credentials, and an approved packet with `final_publish_ready = true`.

```bash
python -m app.main --portal-smoke-test outputs/review_packets_approved/<approved-packet-folder> --dry-run
python -m app.main --portal-smoke-test outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
python -m app.main --verify-portal-item <item-id> --approved-packet outputs/review_packets_approved/<approved-packet-folder>
```

The smoke-test verifier checks that the item is private, not public, not shared to the organization, is a Web Map, has AutoMap draft tags, and uses the approved layer URLs. AutoMap does not overwrite or delete ArcGIS items. Cleanup is manual in Portal.

## Frontend JSON API

The FastAPI backend exposes JSON-only routes for the Next.js frontend:

```text
GET /api/status
GET /api/catalog/search?q=flood
GET /api/data-gaps
GET /api/data-gaps/{gap_key}/candidates
POST /api/data-gaps/resolve
GET /api/external-sources
POST /api/external-sources/load
POST /api/external-sources/inspect
GET /api/history
GET /api/packets
GET /api/preview-config/{packet_id}
POST /api/recipe
POST /api/review-packet
POST /api/webmap-draft
POST /api/analysis/plan
POST /api/analysis/execute
GET /api/analysis/runs
GET /api/analysis/runs/{analysis_run_id}
POST /api/adjustment-template
POST /api/apply-adjustments
POST /api/approval-template
POST /api/apply-approval
POST /api/publish-dry-run
POST /api/portal-smoke-test-dry-run
```

API responses are sanitized and do not expose database URLs, ArcGIS credentials, `.env` values, or protected external-project references. No real publish endpoint is exposed to the frontend API.

## Local Web UI

AutoMap v0.8 adds a local FastAPI/Jinja web interface for the draft workflow.

```bash
python -m app.main --serve-ui
```

Open:

```text
http://127.0.0.1:8010
```

AutoMap defaults to backend/API port `8010`. Ports `3000` and `8000` are reserved for Cabarrus FutureScape and must not be used by AutoMap.

```bash
python -m app.main --serve-ui --ui-port 8010
```

The UI can create recipes, review packets, WebMap drafts, adjustment templates, adjusted packets, catalog searches, data gap views, dry-run publish receipts, and dry-run smoke-test receipts. The UI is local only. It does not real-publish ArcGIS items, does not require ArcGIS login, and does not ingest geometries.

## Live Local Map Preview

AutoMap v0.9 adds a browser map preview for local draft WebMap JSON files.

```bash
python -m app.main --serve-ui --ui-port 8010
python -m app.main --list-packets
python -m app.main --preview-packet outputs/review_packets/<packet-folder> --ui-port 8010
python -m app.main --generate-report outputs/review_packets_approved/<approved-packet-folder>
python -m app.main --list-reports
python -m app.main --validate-report outputs/reports/<report-folder>
```

Preview routes:

```text
http://127.0.0.1:8010/preview
http://127.0.0.1:8010/preview/<packet-id>
```

The preview uses draft WebMap JSON and verified ArcGIS REST layer URLs. It does not publish anything, does not require ArcGIS login, and is for human GIS review only.

## v1 Demo Workflow

Run the full safe local demo flow:

```bash
python -m app.main --run-demo-workflow
```

Check local system status:

```bash
python -m app.main --system-status
```

Start the v1 local UI:

```bash
python -m app.main --serve-ui --ui-port 8010
```

Useful pages:

```text
http://127.0.0.1:8010/demo
http://127.0.0.1:8010/status
http://127.0.0.1:8010/history
http://127.0.0.1:8010/approval
http://127.0.0.1:8010/preview
```

## Architecture

```text
Prompt -> Parser -> Layer Matcher -> Recipe Engine
       -> Field/Filter Intelligence -> Draft WebMap JSON
       -> Review Packet -> Human Adjustment -> Local Preview
       -> Reviewer Approval -> Dry-Run Receipt
       -> Controlled Private ArcGIS Draft Publish
       -> Portal Smoke-Test Verification
       -> Next.js Frontend Workflow Shell
       -> UX-Polished Local Map Preview
       -> Report And Export Center
       -> Safe Spatial Analysis Execution
       -> Data Gap Resolver And External Source Review
```

The trusted source for layer selection is `automap.layer_catalog`. Generated artifacts live under `outputs/`, which is ignored by Git.

See:

- `docs/v1_demo_workflow.md`
- `docs/project_architecture.md`
- `docs/safety_model.md`
- `docs/portal_smoke_test.md`
- `docs/frontend_app_shell.md`
- `docs/frontend_ux_design.md`
- `docs/map_preview_frontend.md`
- `docs/report_export_center.md`
- `docs/spatial_analysis_execution.md`
- `docs/spatial_query_optimizer.md`
- `docs/analysis_safety_limits.md`
- `docs/data_gap_resolver.md`
- `docs/external_source_connectors.md`

## Notes

- Approved GIS layers come from AutoMap's local `automap.layer_catalog`.
- Generated recipes, WebMap drafts, review packets, adjusted packets, approved packets, and reports are local artifacts and are not committed.
- ArcGIS Online or Portal publishing is dry-run by default and real-publish is CLI-only behind explicit safeguards.
- Spatial analysis outputs are local review GeoJSON files and are not official GIS layers.
- Bounded spatial query optimization uses count/ObjectID-first ArcGIS REST queries and does not download broad countywide parcel datasets.
- CFS uses a separate database and remains untouched by AutoMap.
