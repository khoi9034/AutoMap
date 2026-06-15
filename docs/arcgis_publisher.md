# Safe ArcGIS Draft Publisher

AutoMap v0.7 adds a safe publisher for adjusted review packets.

The default behavior is dry-run only. Dry-run validates the adjusted packet, builds the ArcGIS Web Map item properties, and writes `publish_receipt.json` inside the adjusted packet folder. It does not connect to ArcGIS and does not create any item.

## Safety Rules

- Only adjusted packets can be published.
- Raw review packets are blocked.
- Real publishing requires `--confirm-publish`.
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
```

Confirmed private draft publishing:

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_adjusted/<adjusted-packet-folder> --confirm-publish
```

Do not use confirmed publishing until the adjusted packet is approved for a private ArcGIS draft item.

## Publish Requirements

The adjusted packet must include:

- `adjusted_recipe.json`
- `adjusted_webmap.json`
- `applied_adjustments.json`
- `adjusted_warnings.json`

The adjusted packet must have `publish_ready = true`, and unresolved warnings or publishing blockers must be cleared by human review. Warnings are not deleted; resolved warnings remain in the audit trail.

## Item Properties

AutoMap draft items use:

- Title prefix: `AutoMap Draft -`
- Type: `Web Map`
- Tags: `AutoMap`, `Draft`, `GIS Request Engine`, `Cabarrus County`, `Human Review Required`

## Receipt

Every dry-run or blocked publish writes `publish_receipt.json`. Receipts do not include passwords, tokens, environment values, or database connection strings.

## Project Boundary

The CFS database is separate and must not be touched by AutoMap publishing. AutoMap v0.7 works only with adjusted review packet files and ArcGIS item metadata.
