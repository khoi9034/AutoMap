# Road-Following Route Drafts

AutoMap can draw a road-following draft route for proximity maps when a verified street centerline layer is available and the origin-target corridor is small enough to query safely.

The route engine:

- uses only verified street or centerline layers from the AutoMap catalog
- builds a bounded search extent around the origin and target
- counts centerline features before downloading geometry
- caps centerline downloads at the configured safe limits
- builds a small local graph from the returned linework
- snaps origin and target to the nearest graph nodes
- writes `route_line.geojson` when the graph route succeeds
- keeps `straight_line.geojson` as a reference/fallback output

Composer previews prefer `route_line.geojson` when it exists. The legend then shows `Road-following draft route`, the line draws solid with a casing, and the straight-line reference is hidden by default. If the bounded road graph fails, AutoMap keeps the dashed straight-line reference and warns that it is not a road route.

These routes are draft GIS review aids only. They are not official navigation, emergency response routing, turn-by-turn directions, or an ArcGIS-published network analysis result.

Outputs remain local under `outputs/proximity/` and are ignored by Git. CFS remains separate and `cfs_dev` is not touched.
