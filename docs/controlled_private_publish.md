# Controlled Private ArcGIS Publish

AutoMap v1.2 can create a private draft ArcGIS Web Map item from an approved packet. This is the first controlled real publish step.

Dry-run remains the default. Real publishing is CLI-only and requires explicit safeguards.

## What v1.2 Can Publish

Only approved packets can be real-published:

```text
outputs/review_packets_approved/<approved-packet-folder>/
```

The approved packet must include:

- `approved_recipe.json`
- `approved_webmap.json`
- `approval_receipt.json`
- `approved_warnings.json`

The approval receipt must have:

- `final_publish_ready = true`
- no unresolved block reasons

Raw review packets and adjusted packets cannot be real-published.

## Environment

Copy `.env.example` to `.env` and fill values locally. Do not commit `.env`.

```text
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_USERNAME=your_username
ARCGIS_PASSWORD=your_password
ARCGIS_TARGET_FOLDER=AutoMap Drafts
ARCGIS_PUBLISH_ENV=dev
AUTOMAP_PUBLISH_DRY_RUN=true
AUTOMAP_ALLOW_REAL_PUBLISH=false
```

`ARCGIS_PORTAL_URL` is configurable because the organization may move between ArcGIS portals.

Supported publish profiles:

- `dev`: allowed for controlled testing when all real-publish flags are enabled.
- `staging`: optional controlled staging profile.
- `production`: blocked unless `AUTOMAP_ALLOW_REAL_PUBLISH=true` and `--confirm-publish` are both present.

## Dry-Run

Dry-run never connects to ArcGIS and never creates an item.

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --dry-run
```

Dry-run writes `publish_receipt.json` inside the approved packet folder.

## Real Publish

Real publish requires all of the following:

- approved packet folder only
- `approval_receipt.final_publish_ready = true`
- no approval block reasons
- `--confirm-publish`
- `AUTOMAP_ALLOW_REAL_PUBLISH=true`
- `AUTOMAP_PUBLISH_DRY_RUN=false`
- ArcGIS credentials configured
- target folder configured

Command:

```bash
python -m app.main --publish-draft-webmap outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
```

If any requirement fails, AutoMap blocks publishing, writes `publish_receipt.json`, and does not connect to ArcGIS when packet or environment gates fail.

## Private Item Rules

When real publishing is allowed, AutoMap:

- creates a new Web Map item
- uses existing operational layer URLs from `approved_webmap.json`
- creates or uses `ARCGIS_TARGET_FOLDER`
- keeps the item private
- does not share publicly
- does not share to the organization
- does not overwrite existing items
- does not update existing items
- does not delete items
- does not publish layers
- does not create Experience Builder apps

Item tags:

- `AutoMap`
- `Draft`
- `GIS Request Engine`
- `Cabarrus County`
- `Human Review Required`

## Receipt

`publish_receipt.json` includes:

- dry-run status
- whether real publish was attempted
- whether an item was created
- item id and URL when mocked or real publish succeeds
- portal URL
- target folder
- item title
- public and organization sharing flags
- overwrite and delete flags
- approved packet path
- approval receipt summary
- selected layers
- definition expressions
- warning summary
- reviewer name
- published timestamp
- block reasons
- protected database boundary flag

Receipts must not include ArcGIS credentials, tokens, `.env` values, or database connection strings.

## Project Boundary

AutoMap uses its own local database and schema. The CFS database `cfs_dev` is separate and must not be connected to, inspected, modified, migrated, or written by AutoMap publishing.
