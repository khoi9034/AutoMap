# AutoMap: County GIS Request Engine

AutoMap converts plain-English county GIS map requests into structured map recipes using only approved GIS layers from a local layer catalog.

Version: `1.3.0`

## Current Phase

v1.3 portal publish smoke test and item verification.

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
- controlled private ArcGIS Web Map publishing from approved packets
- one-item private Portal smoke-test verification
- local request history and system status

## What AutoMap Does Not Do Yet

AutoMap does not ingest full feature geometries, does not download full feature datasets, does not publish from the local UI, does not publish publicly, does not share to the organization, and does not use an external LLM API.

ArcGIS publishing and smoke testing remain dry-run by default unless a guarded CLI path is explicitly confirmed with an approved packet and local environment safety flags.

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

```bash
python -m app.main --make-recipe "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --make-recipe "Map recent permits and planning cases near Kannapolis."
python -m app.main --make-recipe "Show school districts for parcels in Harrisburg."
python -m app.main --make-recipe "Show commercial zoning around Concord."
python -m app.main --make-recipe "Show 2014 parcels and zoning."
```

Use `--save-recipe` with `--make-recipe` to write a local JSON recipe under `outputs/sample_recipes/`. Generated outputs are local artifacts and are not committed.

## Field Intelligence And Filter Planning

AutoMap v0.3 profiles real ArcGIS REST fields and small non-geometry value samples so recipes can include executable filter plans. Sampling uses `returnGeometry=false`; AutoMap still does not ingest full geometries or generate ArcGIS web maps.

```bash
python -m app.main --profile-layer-fields --layer-key cabarrus_new_cabarrus_county_zoning_0_cabarrus_county_zoning
python -m app.main --profile-catalog-fields
python -m app.main --profile-catalog-fields --category zoning
python -m app.main --validate-recipe "Show parcels in Concord that are in the 100-year floodplain."
python -m app.main --list-data-gaps
```

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
http://127.0.0.1:8001/approval
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

## Local Web UI

AutoMap v0.8 adds a local FastAPI/Jinja web interface for the draft workflow.

```bash
python -m app.main --serve-ui
```

Open:

```text
http://127.0.0.1:8000
```

If port `8000` is already occupied by another local service, use a temporary local override:

```bash
python -m app.main --serve-ui --ui-port 8001
```

The UI can create recipes, review packets, WebMap drafts, adjustment templates, adjusted packets, catalog searches, data gap views, dry-run publish receipts, and dry-run smoke-test receipts. The UI is local only. It does not real-publish ArcGIS items, does not require ArcGIS login, and does not ingest geometries.

## Live Local Map Preview

AutoMap v0.9 adds a browser map preview for local draft WebMap JSON files.

```bash
python -m app.main --serve-ui --ui-port 8001
python -m app.main --list-packets
python -m app.main --preview-packet outputs/review_packets/<packet-folder> --ui-port 8001
```

Preview routes:

```text
http://127.0.0.1:8001/preview
http://127.0.0.1:8001/preview/<packet-id>
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
python -m app.main --serve-ui --ui-port 8001
```

Useful pages:

```text
http://127.0.0.1:8001/demo
http://127.0.0.1:8001/status
http://127.0.0.1:8001/history
http://127.0.0.1:8001/approval
http://127.0.0.1:8001/preview
```

## Architecture

```text
Prompt -> Parser -> Layer Matcher -> Recipe Engine
       -> Field/Filter Intelligence -> Draft WebMap JSON
       -> Review Packet -> Human Adjustment -> Local Preview
       -> Reviewer Approval -> Dry-Run Receipt
       -> Controlled Private ArcGIS Draft Publish
       -> Portal Smoke-Test Verification
```

The trusted source for layer selection is `automap.layer_catalog`. Generated artifacts live under `outputs/`, which is ignored by Git.

See:

- `docs/v1_demo_workflow.md`
- `docs/project_architecture.md`
- `docs/safety_model.md`
- `docs/portal_smoke_test.md`

## Notes

- Approved GIS layers come from AutoMap's local `automap.layer_catalog`.
- Generated recipes, WebMap drafts, review packets, and adjusted packets are local artifacts and are not committed.
- ArcGIS Online or Portal publishing is dry-run by default in v1.3 and real-publish is CLI-only behind explicit safeguards.
- CFS uses a separate database and remains untouched by AutoMap.
