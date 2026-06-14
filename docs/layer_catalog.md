# AutoMap Layer Catalog

The AutoMap layer catalog lives in `automap.layer_catalog` in the local AutoMap PostGIS database.

## Priority

New separated OpenData layers use `source_priority = 1`.

Legacy monolithic OpenData layers use `source_priority = 2`. They are retained for fallback and historical metadata, but should not be preferred over verified new OpenData records for normal current map requests.

## Layer Keys

New OpenData layer keys use:

```text
cabarrus_new_{service_name_slug}_{layer_id}_{layer_name_slug}
```

Legacy layer keys use:

```text
cabarrus_legacy_opendata_{layer_id}_{layer_name_slug}
```

## Historical Layers

Legacy layer names containing years from 2004 through 2015 are marked:

- `is_historical = true`
- `historical_year = detected year`
- `source_status = legacy_historical`

Historical layers are not active by default. They can be used later when a user asks for historical, archive, past-year, or specific-year maps.

## Metadata Only

AutoMap stores REST metadata, layer fields, drawing info, capabilities, extents, source priority, verification status, and optional count results. It does not store full geometries or feature datasets yet.

