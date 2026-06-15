# Analysis Safety Limits

AutoMap v2.0 spatial execution is count-first, bounded, local, and reviewable.

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
- fetches geometry only after count checks pass
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

v2.0 prefers local GeoJSON output. Geometry table storage is optional and should only be used for small, safe results.

## Publishing Rules

Spatial analysis does not publish anything.

Derived GeoJSON is:

- local only
- ignored by Git
- not uploaded to Portal
- not an official GIS layer
- shown with a review badge in the frontend

The CFS database is separate and untouched.
