# AutoMap: County GIS Request Engine

AutoMap converts plain-English county GIS map requests into structured map recipes using only approved GIS layers from a local layer catalog.

Version: `4.9.0`

## Current Phase

v4.9 Locked Map Navigation Outside Adjust Step and Map Frame Titles on top of live Print / Export preview, WYSIWYG print export, table requests, exact composer map state preservation, enterprise UI layout cleanup, step-specific Map Composer layouts, enterprise centered scale bar and final map layout polish, county exhibit and staff report map layouts, enterprise cartography, road-following route drafts, semantic Map Composer symbols, real map composer preview rendering, derived GeoJSON overlays, the four-step composer, address-to-parcel resolver, proximity, real parcel lookup, parcel workspace, scenario workbench, planning scenario and suitability intelligence, development/transportation source intelligence, real source verification, data gap resolution, analysis summary reporting, and user-guided safe spatial analysis refinement.

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
- metadata-only source discovery and verification for real REST endpoints, with proxy/limited-coverage gap closure rules
- source coverage intelligence that labels official, proxy, reference, limited-coverage, historical, and missing official sources
- development and transportation request handling for AADT, STIP, Accela/plan-review proxy activity, and Concord-limited planning cases
- planning scenario and suitability frameworks with transparent reviewable weights, assumptions, source warnings, and local report exports
- scenario workbench variants, reviewer weight tuning, scenario comparison, and scenario-to-recipe conversion
- real parcel lookup for PIN/PIN14/parcel ID/address inputs, selected parcel GeoJSON output, context overlays, and local parcel reports
- proximity, nearest-facility, containing-district, and straight-line route draft workflows with local GeoJSON/report outputs
- simple Map Composer workflow for prompt, preview, adjustment, and print/export
- parcel-focused preview blocking until a parcel is matched
- address-focused prompts resolved through progressive verified address/parcel field matching, normalized variants, bounded candidates, and no owner-name lookup by default
- nearest-facility address prompts routed to straight-line proximity drafts when safe
- clean composer blocked states that hide adjust/export controls until preview is ready
- composer preview rendering with a real ArcGIS basemap, REST context layers, and local derived GeoJSON overlays for origin points, selected parcels, nearest facilities, and straight-line distance lines
- conservative fire/EMS targeting that warns when a verified source cannot prove a fire-only facility filter
- bounded road-following route drafts from verified street centerlines when safe, with dashed straight-line fallback when not
- semantic Map Composer symbols for origin homes, fire stations, schools, hospitals, parks, libraries, generic facilities, route lines, and selected parcels
- proximity preview clutter reduction that hides full address/parcel/facility context layers by default while keeping derived result overlays visible
- enterprise Map Composer cartography with title block, legend, scale bar, north arrow, route casing, marker-on-top draw order, and print-ready draft layout
- refined enterprise map layout with concise request-specific titles, in-frame legend, adaptive labeled imperial scale bar, compact north arrow, and matching print composition
- county exhibit and staff-report-style exports with title blocks, map frames, source tables, warning summaries, draft disclaimers, browser print layout, and local exhibit packages
- centered enterprise scale bar spanning about 64% of the map frame, with readable feet/mile labels and print/exhibit placement
- step-specific Map Composer layouts so Request, Preview, Adjust, and Print / Export each use the workspace that fits that task
- enterprise Map Composer scroll behavior where the desktop workbench fills the viewport, the map remains visible, and only the right-side control panel scrolls when needed
- saved composer map state so print layouts, exhibit packages, and reports preserve the exact adjusted map title, extent, basemap, visible layers, opacity, order, symbology, legend, scale bar, north arrow, warnings, and notes
- optional report/statistics sections that summarize available map metadata honestly and mark unresolved permit/planning/development data as unavailable instead of inventing counts
- live Print / Export preview with controls on the left, a scrollable final-page preview on the right, and optional report sections that update before printing
- locked map interaction modes so Preview and Print / Export are read-only while Adjust is the only pan/zoom step that can set the final map extent
- map-frame titles shown directly inside the map canvas frame for preview, adjustment, and print/export consistency
- table/data request classification for parcel lists, permit tables, zoning records, historical tables, attribute tables, data exports, and combined map+table requests
- bounded Table Center previews and local CSV/JSON/Markdown exports using verified catalog layers, selected real fields, count-first safety limits, and `returnGeometry=false`
- historical table handling that can use verified legacy layers for requested years while keeping unresolved current permit gaps honest

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
25. v2.5 real source verification and gap closure
26. v2.6 development and transportation source intelligence
27. v2.7 planning scenario and suitability intelligence
28. v2.8 scenario workbench and weight tuning
29. v2.9 parcel workspace and parcel-centered map requests
30. v3.0 real parcel lookup and selected parcel context maps
31. v3.1 proximity, nearest facility, and route drafts
32. v3.2 simplified workflow and parcel-focused preview
33. v3.3 simple map composer workflow and true preview behavior
34. v3.4 four-step map composer UI
35. v3.5 clean composer UI and address-to-parcel resolver
36. v3.6 real composer map rendering for address, parcel, and proximity outputs
37. v3.7 real map composer preview and facility target fix
38. v3.8 road-following route drafts and semantic map symbols
39. v3.9 enterprise cartography and print layout
40. v4.0 enterprise map layout refinement
41. v4.1 county exhibit and staff report map layout
42. v4.2 enterprise centered scale bar and final map layout polish
43. v4.3 step-specific map composer layouts
44. v4.4 enterprise UI layout and scroll behavior cleanup
45. v4.5 print/report uses exact composer map state
46. v4.6 table request engine and export center

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

AutoMap v3.1 adds proximity, nearest-facility, and route-draft workflows to the Next.js + TypeScript shell under `frontend/`. The FastAPI backend remains the API and workflow engine, and the existing FastAPI/Jinja UI is preserved.

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

Visible frontend pages:

- `/dashboard`
- `/map-composer`
- `/parcel-workspace`
- `/proximity`
- `/scenarios`
- `/analysis`
- `/reports`
- `/layer-catalog`
- `/data-gaps`
- `/external-sources`
- `/history`
- `/system-status`

Internal workflow routes such as `/map-request`, `/clarify`, `/recipe-review`, `/map-preview`, `/adjustments`, `/approval`, and `/publish-center` redirect to `/map-composer` by default. The normal user-facing workflow is:

```text
Request -> Preview -> Adjust -> Print / Export
```

The frontend does not expose real publish controls. Real publish remains CLI-only.

The visible workflow shell includes an operations dashboard, Map Composer, parcel workspace, proximity tools, scenario builder, analysis tools, report/export center, catalog search, data gaps, external source review, history, and sanitized system status. Internal recipe, packet, adjustment, approval, dry-run publish, learning, and detailed preview tools remain implementation capabilities but are not part of the normal sidebar.

The Scenario Workbench page lets reviewers tune scenario weights, enable or disable factors, add reviewer assumptions, save variants, compare scenarios/variants, and convert a reviewed scenario into a draft map recipe. Scenario scores are planning-support drafts, not official recommendations. Proxy sources remain context only unless reviewed, missing official permit data remains unresolved, and no geometry scoring runs from the workbench.

Map Composer surfaces request intelligence details such as detected intents, confidence by intent, spatial relationships, ambiguity flags, clarifying questions, unsupported parts, and the analysis plan in the simplified flow where useful. This is deterministic rule-based interpretation only; AutoMap does not call external LLM APIs.

The clarification engine turns those clarifying questions into an interactive local review loop behind the composer. Staff can answer distance, flood-scope, missing-data, recent-time, and zoning-code questions, then AutoMap regenerates request intelligence, the analysis plan, selected layers, filters, warnings, and the map recipe. The original recipe remains available for comparison, and the refined recipe records what changed.

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

AutoMap persists the active local composer/workflow state in browser storage so staff can move from prompt to preview, adjustment, and export without losing context on refresh. The stored workflow state is sanitized and does not include secrets.

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

For production backend deployment, AutoMap can use Supabase PostGIS. Local machines can use the Supabase Dashboard -> Connect -> Direct Postgres connection string converted to `postgresql+psycopg2://...`. Render should use the Supabase Session Pooler URL when Direct IPv6 connectivity fails, also converted to `postgresql+psycopg2://...`, with the `postgres.mjfbpmatxvjczikqbuva` pooler username and `postgres` database name. Set this as backend-only `DATABASE_URL`. Do not put the Supabase database password or service role key in frontend env.

Safe deployment initialization:

```bash
python -m app.main --deployment-init-db
python -m app.main --deployment-seed-catalog
```

Deployment docs:

- `docs/supabase_postgis_setup.md`
- `docs/deployment_backend_env.md`
- `docs/deployment_backend_render.md`
- `docs/deployment_backend_railway.md`
- `docs/deployment_vercel_frontend.md`

After the backend is deployed, set the Vercel server-side proxy target:

```text
AUTOMAP_API_SERVER_URL=https://automap-api.onrender.com
```

Production browser API requests go to the same-origin proxy path `/api/automap/*`,
which forwards to Render. Keep `NEXT_PUBLIC_AUTOMAP_API_BASE_URL=https://automap-api.onrender.com`
only as a browser-safe display value if needed. Do not expose database URLs or set
production API values to localhost.

## Render Backend Deployment

AutoMap can deploy the FastAPI backend to Render as a Python Web Service using the root `render.yaml`.

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.web_ui:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

Set `DATABASE_URL` as a Render secret using the Supabase Session Pooler SQLAlchemy URL for the `mjfbpmatxvjczikqbuva` project. Keep `AUTOMAP_PUBLISH_DRY_RUN=true` and `AUTOMAP_ALLOW_REAL_PUBLISH=false`.

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

AutoMap v2.5 adds metadata-only source discovery and verification to the local external source registry for important missing-data needs:

- current permits
- current planning cases
- current development pipeline
- plan review / Accela pipeline signals
- AADT traffic counts
- STIP transportation projects

Sources are marked `approved`, `candidate`, or `needs_review`, and as `active`, `proxy`, `reference`, or `legacy`. Candidate and proxy sources can improve review context, but they do not silently resolve official permit, planning case, or development pipeline gaps.

Verified v2.5 sources include NCDOT AADT, NCDOT STIP, a Cabarrus Accela plan-review proxy, and a Concord-limited planning case layer. Current permits still need an official verified source, Concord planning cases remain limited coverage, and plan reviews remain proxy/context only.

```bash
python -m app.main --load-external-sources
python -m app.main --inspect-external-sources
python -m app.main --discover-sources
python -m app.main --discover-sources --keyword permits
python -m app.main --discover-sources --keyword planning
python -m app.main --discover-sources --keyword accela
python -m app.main --verify-external-source ncdot_aadt_reference
python -m app.main --verify-all-external-sources
python -m app.main --list-external-sources
python -m app.main --resolve-data-gaps
python -m app.main --gap-candidates current_permits
python -m app.main --gap-candidates current_planning_cases
python -m app.main --gap-candidates current_development_pipeline
```

The frontend Data Gaps page shows open, partial, resolved, and needs-review statuses with candidate sources and limitation badges. The External Sources page shows the local registry, discovery results, and metadata verification status.

Metadata inspection uses REST metadata, fields, domains, counts, and non-geometry checks only. AutoMap does not download full feature datasets, does not bulk-ingest data, and does not treat proxy pipeline data as official development approval.

## Development and Transportation Intelligence

AutoMap v2.6 uses verified external sources more carefully in recipes, review packets, WebMap drafts, reports, and frontend panels:

- AADT is selected for traffic-volume and high-traffic corridor context.
- STIP is selected for planned transportation project context.
- Accela and plan-review activity are labeled as proxy activity and never treated as official permit approval.
- Concord planning cases are labeled as limited coverage and are used only with a coverage warning.
- Official current permit data remains unresolved unless a verified official current permit source exists.

```bash
python -m app.main --make-recipe "Show high traffic corridors and nearby development activity."
python -m app.main --make-recipe "Map commercial growth opportunities near high traffic roads."
python -m app.main --make-recipe "Show planned road projects near development pressure areas."
python -m app.main --make-recipe "Show current permits near Kannapolis."
python -m app.main --make-recipe "Show planning cases around Concord."
```

Recipes include `source_coverage` with official, proxy, limited-coverage, reference, historical, and missing-official source groups. See `docs/source_coverage_model.md` and `docs/development_transportation_intelligence.md`.

## Planning Scenarios And Suitability

AutoMap v2.7 builds transparent planning scenario frameworks for growth, suitability, constraints, transportation access, development pressure, school context, planning cases, and historical change. These are reviewable frameworks, not official recommendations or entitlement decisions.

```bash
python -m app.main --make-scenario "Map commercial growth opportunities near high traffic roads but avoid floodplain."
python -m app.main --make-scenario "Show development pressure near schools and flood zones in Concord."
python -m app.main --make-scenario "Find areas suitable for residential growth but avoid flood risk."
python -m app.main --list-scenarios
python -m app.main --generate-scenario-report <scenario_id>
```

Scenario reports are written under `outputs/scenario_reports/` and include HTML, Markdown, JSON, CSV scoring framework, source coverage JSON, and a manifest. Generated reports are ignored by Git.

Scenario scoring is plan-only by default. AutoMap does not execute countywide parcel scoring, does not raise safety limits to force execution, and does not download full datasets. If execution is requested later, it must go through the existing bounded analysis planner and safety limits.

## Scenario Workbench And Weight Tuning

AutoMap v2.8 adds scenario variants, reviewer weight tuning, comparison summaries, and scenario-to-recipe conversion.

```bash
python -m app.main --create-scenario-variant <scenario_id> --params-json '{""variant_name"":""Road access priority"",""weight_overrides"":{""aadt_high_traffic"":40,""floodplain_avoidance"":-30}}'
python -m app.main --list-scenario-variants
python -m app.main --compare-scenarios --scenario-ids "<scenario_id>" --variant-ids "<variant_id>"
python -m app.main --scenario-to-recipe <scenario_id>
python -m app.main --scenario-to-recipe <scenario_id> --variant-id <variant_id>
```

The `/scenario-workbench` frontend page supports opening existing scenarios, editing factor weights, enabling/disabling factors, saving variants, comparing variants, and converting a scenario or variant into a draft map recipe. Conversion preserves source coverage warnings, proxy warnings, missing official data, and the official-use disclaimer. It does not publish, score geometry, or require ArcGIS login.

See `docs/planning_scenarios.md`, `docs/suitability_scoring.md`, `docs/scenario_workbench.md`, and `docs/scenario_weight_tuning.md`.

## Parcel Workspace And Parcel Context Maps

AutoMap v3.0 adds real parcel lookup for PINs, PIN14s, parcel IDs, addresses, pasted parcel lists, and prompts such as `my parcels` or `these parcels`.

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

The `/parcel-workspace` frontend page supports field profiling, parsing identifiers, matching real parcel/address inputs, showing ambiguous candidates, fetching selected parcel GeoJSON when safe, selecting context overlays, setting a nearby distance, generating a selected-parcel context recipe, and exporting local parcel reports.

Parcel matching uses verified Tax Parcels and Addresses fields from the AutoMap catalog and field profiles. It runs `returnGeometry=false` count/attribute checks first, preserves unmatched identifiers, marks multiple matches for review, and does not download countywide parcel geometry. Selected parcel geometry is fetched only after the matched count is safely bounded, with a default selected-geometry limit of 100 parcels and a hard max of 250.

Selected parcel GeoJSON outputs are written under `outputs/parcel_context/`, and parcel reports are written under `outputs/parcel_reports/`. Both are ignored by Git and are local review drafts only. Current permits remain unresolved unless an official verified source is added; Accela/plan-review sources remain proxy context, and Concord planning cases remain limited coverage.

See `docs/parcel_workspace.md`, `docs/parcel_context_maps.md`, `docs/real_parcel_lookup.md`, and `docs/selected_parcel_context_maps.md`.

## Proximity, Nearest Facility, And Route Drafts

AutoMap v3.1 adds bounded proximity workflows from parcel/PIN/address origins to verified facility and district layers.

```bash
python -m app.main --proximity "How far is parcel 5528-12-3456 from the nearest school?"
python -m app.main --nearest-facility "parcel 5528-12-3456" --target nearest_school
python -m app.main --nearest-facility "65 Church St S" --target nearest_fire_station
python -m app.main --route-draft "Draw a route from 65 Church St S to 123 Main St"
python -m app.main --list-proximity-results
python -m app.main --validate-proximity-result <proximity_result_id>
```

The `/proximity` frontend page supports origin input, target selection, straight-line nearest-facility requests, route drafts, result cards, warnings, and local output links. `/parcel-workspace` also includes parcel-origin actions for nearest school, nearest fire station, containing fire district, and route draft to address.

Nearest-facility searches use bounded distance rings and candidate caps. AutoMap tries a bounded road-following draft with verified street centerlines when safe, writes `route_line.geojson` on success, and keeps the dashed straight-line reference as fallback only. These drafts are not official driving directions. Outputs are written under `outputs/proximity/`, ignored by Git, and are local draft files only.

See `docs/proximity_nearest_facility.md`, `docs/route_draft_modes.md`, `docs/road_following_route_drafts.md`, and `docs/route_drafts.md`.

## Simple Map Composer And True Preview Behavior

AutoMap v3.4 makes `/map-composer` the primary local path:

```text
Request -> Preview -> Adjust -> Print / Export
```

Composer generation runs request intelligence, builds the technical draft-map artifacts behind the scenes, creates local preview files when preview is valid, and returns one clean response to the frontend. The normal user does not need to jump through Recipe Review, Analysis, Approval, or Publish Center for a basic map request.

For parcel-centered prompts, AutoMap now requires a real parcel/PIN/address match before showing a focused parcel preview. If a parcel is unmatched, the recipe keeps the draft layer plan but marks `can_focus_map=false`, blocks parcel-focused preview/analysis, shows `Parcel not matched`, and asks the user to correct the identifier. It does not zoom to a broad county map as if the parcel were selected.

When a parcel is safely matched, AutoMap fetches only the matched parcel geometry, writes local selected-parcel GeoJSON, computes a small parcel buffer extent, sets the map focus to that extent, and labels context layers as reference around the selected parcel. Analysis remains optional for context maps and still uses bounded safety checks when requested.

AutoMap v4.0 renders composer proximity/address previews with a real ArcGIS Maps SDK map and `streets-vector` basemap. Address/proximity requests show the origin point, nearest facility target, route draft or straight-line reference, and selected parcel outline when one is truly resolved. If an address matches but the related parcel is not resolved from verified fields or a bounded point-in-parcel lookup, the preview still shows the address point and proximity line with a warning instead of pretending the full Tax Parcels layer is the selected property.

Nearest fire station requests use verified facility attributes where possible. If the verified target layer combines Fire and EMS stations and AutoMap cannot confirm a fire-only filter, the result is labeled as nearest Fire/EMS station and includes a review warning. AutoMap tries a bounded road-following draft using verified street centerlines when safe; otherwise it uses a dashed straight-line reference. Neither mode is official turn-by-turn navigation.

Full address, parcel, and target-facility REST layers are hidden by default in proximity previews to reduce clutter. Semantic symbols mark origin homes, facility targets, route lines, and selected parcels. v4.0 refines the professional map frame with a concise title above the map, compact in-frame legend, adaptive labeled imperial scale bar, smaller north arrow, draft disclaimer, and route casing/halo. Route lines draw below selected parcel and facility/origin markers so symbols stay readable. The print page mirrors the preview composition with the focused map, route summary, selected layers, warnings, generated time, and draft-only disclaimer.

AutoMap v4.1 adds county exhibit and staff-report map exports. From Map Composer, `Open Print Layout` renders a print-oriented exhibit page with a professional title block, live map frame, key findings, source notes, layer source table, warning summary, and draft-only disclaimer. `Generate Exhibit Package` writes local files under `outputs/exhibits/<timestamp>_<slug>/`:

- `exhibit.html`
- `exhibit_data.json`
- `layer_sources.csv`
- `warnings.json`
- `export_manifest.json`

The package is local and ignored by Git. Browser print-to-PDF is the supported PDF path for v4.1; AutoMap does not upload or publish exhibit outputs.

AutoMap v4.2 moves the scale bar to the bottom-center of the map frame and makes it a true exhibit-scale element, spanning about 64% of the map width with labeled ticks such as `0 0.25 0.5 mi` or `0 500 1000 ft`. The compact legend stays inside the map frame away from the scale bar, while the north arrow remains top-right.

AutoMap v4.3 gives each Map Composer step its own layout. Request shows the large prompt and examples. Preview focuses on the generated map with compact summary and warnings. Adjust keeps the map on the left while visibility, opacity, layer order, title, route, symbol, and reviewer-note controls stay on the right. Print / Export focuses on local draft outputs and exhibit/report links.

AutoMap v4.4 refines Map Composer into an enterprise workbench. On desktop, the shell fills the viewport, the map canvas does not create its own vertical scrollbar, and the Adjust controls panel is the only composer area that scrolls when the control list exceeds the available height. This keeps the map visible while reviewers tune layers and route styling.

AutoMap also keeps Preview and Print / Export on the same shared map-frame sizing path. Preview is locked/read-only but uses a print-like frame with enough height for the route, origin/target markers, legend, centered scale bar, and north arrow, while Adjust remains the only pan/zoom state for setting the final map view.

Open:

```text
http://localhost:3010/map-composer
```

See `docs/simple_map_composer.md`, `docs/map_preview_behavior.md`, `docs/simplified_workflow.md`, `docs/parcel_focused_preview.md`, `docs/address_matching.md`, `docs/address_to_parcel_resolver.md`, `docs/derived_geojson_preview.md`, `docs/address_proximity_preview.md`, `docs/real_composer_map_preview.md`, `docs/fire_station_targeting.md`, `docs/route_draft_modes.md`, `docs/map_symbology_system.md`, `docs/enterprise_cartography.md`, `docs/map_layout_refinement.md`, `docs/map_title_rules.md`, `docs/print_layout.md`, `docs/wysiwyg_print_export.md`, `docs/live_print_preview.md`, `docs/print_export_options.md`, `docs/exhibit_exports.md`, `docs/staff_report_map_layout.md`, `docs/map_scale_bar.md`, `docs/map_composer_step_layouts.md`, and `docs/enterprise_ui_layout.md`.

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

The normal Next.js UI does not expose approval or publish-center pages. Approval remains a local CLI/internal governance capability, and real Portal publishing is CLI-only.

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

Backend utility pages:

```text
http://127.0.0.1:8010/demo
http://127.0.0.1:8010/status
http://127.0.0.1:8010/history
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
       -> Source Coverage And Transportation/Development Intelligence
       -> Real Parcel Lookup And Selected Parcel Context Maps
       -> Simplified Workflow And Parcel-Focused Preview
       -> Simple Map Composer And True Preview Behavior
       -> Enterprise Cartography And Print Layout
```

The trusted source for layer selection is `automap.layer_catalog`. Generated artifacts live under `outputs/`, which is ignored by Git.

## Production Portfolio Demo

The public frontend is deployed at:

```text
https://auto-map-cyan.vercel.app
```

The Vercel app is the stable recruiter-facing layer. Browser requests go through the same-origin `/api/automap/*` proxy to the Render FastAPI backend, which connects to Supabase PostGIS through the Session Pooler. If Render is asleep or slow on the free tier, the landing page and Map Composer show friendly "backend waking up" messages instead of scary raw errors.

AutoMap is currently a Cabarrus County, NC GIS request engine. Live address search, parcel lookup, and address-based
proximity workflows support Cabarrus County public records only; out-of-county addresses are not treated as a broken app
state and are directed to the static demo or Cabarrus County sample prompts.

Recruiter-safe behavior:

- `/` is a professional project overview with live readiness status.
- `/map-composer` remains usable while the backend wakes.
- The known demo prompt has a static fallback result for portfolio review.
- Static fallback content is clearly labeled and does not claim to be a live GIS output.
- ArcGIS publishing is disabled in the public demo.

Production smoke check:

```bash
python scripts/production_smoke_check.py
```

For resume/interview demos, consider upgrading Render or using uptime monitoring to avoid cold starts. Keep real ArcGIS publishing disabled unless running a deliberately controlled private workflow.

See:

- `docs/v1_demo_workflow.md`
- `docs/project_architecture.md`
- `docs/safety_model.md`
- `docs/portal_smoke_test.md`
- `docs/frontend_app_shell.md`
- `docs/frontend_ux_design.md`
- `docs/map_preview_frontend.md`
- `docs/simple_map_composer.md`
- `docs/map_preview_behavior.md`
- `docs/report_export_center.md`
- `docs/spatial_analysis_execution.md`
- `docs/spatial_query_optimizer.md`
- `docs/analysis_safety_limits.md`
- `docs/data_gap_resolver.md`
- `docs/external_source_connectors.md`
- `docs/verified_external_sources.md`
- `docs/source_coverage_model.md`
- `docs/development_transportation_intelligence.md`
- `docs/planning_scenarios.md`
- `docs/suitability_scoring.md`
- `docs/real_parcel_lookup.md`
- `docs/selected_parcel_context_maps.md`
- `docs/simplified_workflow.md`
- `docs/parcel_focused_preview.md`
- `docs/real_composer_map_preview.md`
- `docs/fire_station_targeting.md`
- `docs/route_draft_modes.md`
- `docs/map_symbology_system.md`
- `docs/enterprise_cartography.md`
- `docs/print_layout.md`

## Notes

- Approved GIS layers come from AutoMap's local `automap.layer_catalog`.
- Generated recipes, WebMap drafts, review packets, adjusted packets, approved packets, and reports are local artifacts and are not committed.
- ArcGIS Online or Portal publishing is dry-run by default and real-publish is CLI-only behind explicit safeguards.
- Spatial analysis outputs are local review GeoJSON files and are not official GIS layers.
- Bounded spatial query optimization uses count/ObjectID-first ArcGIS REST queries and does not download broad countywide parcel datasets.
- CFS uses a separate database and remains untouched by AutoMap.
