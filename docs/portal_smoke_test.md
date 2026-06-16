# AutoMap Portal Publish Smoke Test

AutoMap v1.3 adds a guarded smoke-test workflow for publishing one approved packet as a private ArcGIS Web Map draft, then verifying the created item. The default path is still dry-run only.

## Purpose

The smoke test is a final safety check for the controlled publish workflow. It confirms that an approved AutoMap packet can become a private draft Web Map item and that the item remains private, is not shared publicly, is not shared to the organization, and contains the expected approved WebMap operational layer URLs.

This workflow does not ingest geometries, does not download feature datasets, does not create Experience Builder apps, does not overwrite existing items, and does not delete items.

## Required Packet

Only approved packets can be smoke tested:

```text
outputs/review_packets_approved/<approved-packet-folder>
```

The packet must include:

- `approved_recipe.json`
- `approved_webmap.json`
- `approval_receipt.json`
- `approved_warnings.json`
- `final_publish_ready = true`

Raw review packets and adjusted packets are blocked.

## Dry-Run Smoke Test

Dry-run is the default and does not connect to ArcGIS or create an item.

```bash
python -m app.main --portal-smoke-test outputs/review_packets_approved/<approved-packet-folder> --dry-run
```

The command writes:

```text
outputs/review_packets_approved/<approved-packet-folder>/smoke_test_receipt.json
```

The normal Next.js UI does not expose the approval or publish center pages. Portal smoke testing remains a CLI/internal workflow and never real-publishes from the frontend.

## Real Smoke Test

Real smoke testing is CLI-only and can create at most one private Web Map item. It requires all safety gates:

```text
AUTOMAP_ALLOW_REAL_PUBLISH=true
AUTOMAP_PUBLISH_DRY_RUN=false
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_USERNAME=<local username>
ARCGIS_PASSWORD=<local password>
ARCGIS_TARGET_FOLDER=AutoMap Drafts
```

Then run:

```bash
python -m app.main --portal-smoke-test outputs/review_packets_approved/<approved-packet-folder> --confirm-publish
```

If any gate is missing, AutoMap blocks before connecting to ArcGIS and writes a clear receipt.

## Verification

After a real smoke-test item is created, AutoMap verifies:

- item exists
- item type is `Web Map`
- item title starts with `AutoMap Draft -`
- item access is private
- item is not shared publicly
- item is not shared to the organization
- item tags include AutoMap draft tags
- item data has operational layers
- item operational layer URLs match `approved_webmap.json`
- no protected CFS or secret markers appear

You can verify a previously created item:

```bash
python -m app.main --verify-portal-item <item-id> --approved-packet outputs/review_packets_approved/<approved-packet-folder>
```

## Receipt

`smoke_test_receipt.json` records:

- start and completion timestamps
- dry-run or real attempt
- block reasons
- item id and URL if an item was created
- private/public/org-sharing verification status
- Web Map type and layer URL verification status
- manual cleanup instructions
- CFS untouched statement

Receipts must not contain passwords, tokens, `.env` values, or database secrets.

## Manual Cleanup

AutoMap does not delete smoke-test items automatically. After a real smoke test, manually inspect the private draft item in Portal and delete it manually when testing is complete.

## Safety Boundaries

AutoMap v1.3 does not publish publicly, does not share to the organization, does not overwrite items, does not update existing items, and does not delete items. The CFS database `cfs_dev` is separate and must not be touched.
