# Analysis Safety Limits

AutoMap v2.1 spatial execution is count-first, ObjectID-first, bounded, local, and reviewable.

## Feature Limits

Default max features:

```text
2000
```

Hard max features:

```text
5000
```

If a query count exceeds the selected max, AutoMap blocks execution and asks the reviewer to narrow the request. It does not silently continue.

## REST Query Rules

AutoMap:

- uses `returnGeometry=false` for count and value checks
- prefers `f=geojson` for bounded feature results
- uses POST when large geometry filters would exceed safe URL length
- queries target ObjectIDs before downloading target geometry
- fetches geometry only after count and ObjectID checks pass
- records where clauses and counts in the analysis receipt
- blocks oversized target queries before feature download
- never bulk-downloads full countywide parcel, zoning, flood, or similar datasets

## Geometry Rules

AutoMap uses local Shapely geometry operations on bounded GeoJSON features.

If coordinate systems explicitly conflict, AutoMap stops with a review warning. GeoJSON from ArcGIS REST is expected to be WGS84.

## Database Rules

AutoMap creates additive tables only in its own `automap` schema:

```text
automap.analysis_runs
automap.analysis_result_features
```

v2.1 prefers local GeoJSON output. Geometry table storage is optional and should only be used for small, safe results.

## Optimizer Limits

Default optimizer limits:

```text
max chunks: 25
max features per chunk: 1000
max constraint features: 500
```

If the optimized candidate ObjectID count still exceeds the feature limit, AutoMap blocks and recommends narrowing the request.

## Publishing Rules

Spatial analysis does not publish anything.

Derived GeoJSON is:

- local only
- ignored by Git
- not uploaded to Portal
- not an official GIS layer
- shown with a review badge in the frontend

The CFS database is separate and untouched.
