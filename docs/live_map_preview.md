# Live Local Map Preview

AutoMap v0.9 adds a local browser preview for draft WebMap JSON artifacts.

Start the local UI:

```bash
python -m app.main --serve-ui --ui-port 8010
```

Then open:

```text
http://127.0.0.1:8010
```

## What It Previews

The preview reads local output artifacts only:

- `outputs/review_packets/<packet>/webmap.json`
- `outputs/review_packets_adjusted/<packet>/adjusted_webmap.json`
- generated WebMap JSON files under `outputs/webmaps/`

It uses the ArcGIS Maps SDK for JavaScript in the browser to display the verified ArcGIS REST layer URLs already stored in the draft JSON. No geometries are ingested into PostGIS, and no full feature datasets are downloaded by AutoMap.

## Safety Boundary

The preview is local and review-only. It does not publish ArcGIS items, does not require ArcGIS login, does not share maps publicly, and does not call any external LLM API.

The preview config API returns a sanitized subset of draft metadata: map title, extent, operational layers, warnings, missing data, output-relative packet path, and draft status. It does not return credentials, database URLs, `.env` values, or secret local paths.

## Routes

- `GET /preview`
- `GET /preview/{packet_id}`
- `GET /api/preview-config`

## CLI Helpers

List available local packets:

```bash
python -m app.main --list-packets
```

Print a preview URL for a packet or generated WebMap JSON:

```bash
python -m app.main --preview-packet outputs/review_packets/<packet-folder> --ui-port 8010
```

## Project Boundary

AutoMap uses its own local database and schema. The CFS database `cfs_dev` is separate and must not be touched by this preview workflow.
