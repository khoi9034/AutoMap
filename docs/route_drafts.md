# Route Drafts

AutoMap v3.1 does not calculate road-network routes.

When a user asks for a route, AutoMap creates a draft straight-line reference if the origin and destination can be matched safely. The result is clearly labeled:

`Straight-line reference, not driving route.`

Road-network routing requires an approved routing/network service. AutoMap does not call paid routing APIs, external geocoding APIs, or unapproved network services.

Route draft output includes:

- matched origin summary
- matched destination summary
- straight-line distance
- local GeoJSON line file
- local Markdown/HTML report
- warning that road-network routing is unavailable

Generated route drafts are local review artifacts under `outputs/proximity/` and are ignored by Git. No ArcGIS item is created or published.

CFS remains separate and `cfs_dev` is not touched.
