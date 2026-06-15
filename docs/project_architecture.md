# AutoMap Project Architecture

AutoMap is a local county GIS request engine. It converts a plain-English request into structured review artifacts using only verified metadata from the AutoMap layer catalog.

## Text Architecture Diagram

```text
Plain-English Prompt
        |
        v
Prompt Parser
        |
        v
Layer Matcher  --->  automap.layer_catalog
        |
        v
Recipe Engine
        |
        v
Filter / Field Intelligence  --->  automap.layer_field_profile
        |                         automap.layer_value_profile
        v
Draft WebMap JSON
        |
        v
Review Packet  --->  outputs/review_packets/
        |
        v
Human Adjustment Loop  --->  outputs/review_packets_adjusted/
        |
        v
Local Map Preview
        |
        v
Dry-Run Publisher Receipt
```

## Key Modules

- `app.prompt_parser`: extracts geography, topics, dates, and intent.
- `app.layer_matcher`: selects verified catalog layers.
- `app.recipe_engine`: builds structured map recipes.
- `app.webmap_builder`: creates local draft WebMap JSON.
- `app.review_packet_builder`: writes local human-review packets.
- `app.adjustment_engine`: applies reviewer edits without mutating originals.
- `app.arcgis_publisher`: validates adjusted packets and supports dry-run publishing.
- `app.packet_index`: discovers local packets and builds sanitized preview config.
- `app.web_ui`: serves the local FastAPI/Jinja UI.
- `app.system_status`: returns sanitized local status counts.
- `app.request_history`: records local workflow activity.

## Storage

AutoMap uses its own local PostGIS database and the `automap` schema. Generated files are stored under `outputs/`, which is ignored by Git.

The layer catalog stores ArcGIS REST metadata only. AutoMap does not ingest full feature datasets into PostGIS.
