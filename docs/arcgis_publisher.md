# Safe ArcGIS Draft Publisher

AutoMap v1.2 adds controlled private publishing for reviewer-approved packets.

The default behavior is dry-run only. Dry-run validates the packet, builds the ArcGIS Web Map item properties, and writes `publish_receipt.json` inside the packet folder. It does not connect to ArcGIS and does not create any item.

## Safety Rules

- Raw review packets are blocked.
- Adjusted packets cannot be real-published.
- Approved packets are the v1.2 real-publish target.
- Approved packets must have `final_publish_ready = true`.
- Real publishing requires `--confirm-publish`.
- Real publishing requires `AUTOMAP_ALLOW_REAL_PUBLISH=true`.
- Real publishing requires `AUTOMAP_PUBLISH_DRY_RUN=false`.
- Dry-run is the default.
- Published items must remain private.
- AutoMap does not share items publicly.
- AutoMap does not share items to the organization.
- AutoMap does not overwrite or delete existing ArcGIS items.
- AutoMap does not ingest geometries or download full feature datasets.

## Environment Settings

Copy `.env.example` to `.env` and fill in ArcGIS credentials only when real publishing is intentionally needed.

```text
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_USERNAME=your_username
ARCGIS_PASSWORD=your_password
ARCGIS_TARGET_FOLDER=AutoMap Drafts
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
ARCGIS_PUBLISH_ENV=dev
```

Do not commit `.env`.

## Commands

Check configured ArcGIS credentials:

```bash
python -m app.main --portal-check
```

Dry-run a draft publish:

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_adjusted/<adjusted-packet-folder> --dry-run
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
```

Confirmed private draft publishing:

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
```

Do not use confirmed publishing until the adjusted packet has gone through reviewer approval and the approved packet receipt shows `final_publish_ready = true`.

Confirmed publishing is still blocked unless `.env` also has:

```text
AUTOMAP_ALLOW_REAL_PUBLISH=true
AUTOMAP_PUBLISH_DRY_RUN=false
```

## Publish Requirements

Adjusted packets must include:

- `adjusted_recipe.json`
- `adjusted_webmap.json`
- `applied_adjustments.json`
- `adjusted_warnings.json`

Adjusted packets can be dry-run validated, but they cannot be real-published.

Approved packets must include:

- `approved_recipe.json`
- `approved_webmap.json`
- `approval_file.json`
- `approval_receipt.json`
- `approved_warnings.json`

The approval receipt must have `final_publish_ready = true` and no remaining block reasons.

## Item Properties

AutoMap draft items use:

- Title prefix: `AutoMap Draft -`
- Type: `Web Map`
- Tags: `AutoMap`, `Draft`, `GIS Request Engine`, `Cabarrus County`, `Human Review Required`

## Receipt

Every dry-run, blocked publish, or successful private draft publish writes `publish_receipt.json`. Receipts include item id and URL on success, selected layers, definition expressions, warning summaries, approval receipt summary, sharing flags, overwrite/delete flags, and block reasons. Receipts do not include passwords, tokens, environment values, or database connection strings.

## Portal Profiles

`ARCGIS_PUBLISH_ENV` supports:

- `dev`
- `staging`
- `production`

Production is blocked unless `AUTOMAP_ALLOW_REAL_PUBLISH=true` and `--confirm-publish` are both present.

## Project Boundary

The CFS database is separate and must not be touched by AutoMap publishing. AutoMap v1.2 publishing works with approved packet files and ArcGIS item metadata only.
