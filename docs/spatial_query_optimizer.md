# Bounded Spatial Query Optimizer

AutoMap v2.1 improves safe spatial execution with server-side spatial filtering and ObjectID-first target retrieval.

## Purpose

The optimizer prevents broad parcel downloads when a request can be narrowed by a constraint layer.

For a request such as:

```text
Show parcels in Concord that are in the 100-year floodplain.
```

AutoMap now:

1. Filters `MunicipalDistrict` to the requested municipality when a safe field is available.
2. Queries `FloodPlain100year` features intersecting that geography.
3. Queries parcel ObjectIDs against the narrowed floodplain geometries.
4. Deduplicates parcel ObjectIDs.
5. Downloads parcel geometry only if the final ObjectID count is under the safety limit.
6. Writes a local GeoJSON and receipt only for safe completed runs.

## Strategies

Preferred strategy:

- `geometry_first`

Chunked fallback:

- `chunked_geometry_first`

Extent fallback:

- `extent_first`

Extent fallback is used only as reviewable planning metadata. If it is too broad, execution blocks and asks for refinement.

## Safety

The optimizer keeps the existing conservative limits:

- max download features per layer: `2000`
- hard max download features: `5000`
- max chunks: `25`
- max features per chunk: `1000`
- max constraint features: `500`

If optimized candidates still exceed the limit, AutoMap blocks instead of downloading target geometries.

## Receipts

Analysis receipts include:

- strategy used
- broad target count
- optimized candidate count
- constraint feature count
- chunks used
- selected ObjectID count
- downloaded feature count
- safety checks
- narrowing suggestions

## Boundaries

AutoMap does not bulk-ingest countywide parcels, publish derived results, upload GeoJSON to Portal, or require ArcGIS login.

The CFS database is separate and untouched.
