# ArcGIS REST Catalog Inspector

AutoMap v0.1.1 uses verified ArcGIS REST metadata to build its local layer catalog. The inspector reads configured REST sources, discovers MapServer services, parses each MapServer's live `layers` array, verifies each layer metadata endpoint, and optionally stores a lightweight record count.

## Sources

AutoMap reads `data/rest_sources.seed.json`.

- `cabarrus_new_opendata`: the newer separated Cabarrus OpenData services folder.
- `cabarrus_legacy_opendata`: the legacy monolithic OpenData MapServer.

New OpenData separated services are preferred because they are the current publishing pattern. The legacy monolithic service is retained as fallback and historical metadata.

## Commands

Inspect REST sources without writing to the database:

```bash
python -m app.main --inspect-rest-sources
```

Build or update `automap.layer_catalog` from REST metadata:

```bash
python -m app.main --build-catalog-from-rest
```

Re-check stored layer URLs:

```bash
python -m app.main --verify-layer-catalog
```

Search the verified catalog:

```bash
python -m app.main --search-layers flood
```

## Safety Boundaries

- No full feature datasets are downloaded.
- No geometries are ingested.
- No ArcGIS web maps are created.
- CFS is separate and was not touched.
- AutoMap refuses the protected `cfs_dev` database name.

