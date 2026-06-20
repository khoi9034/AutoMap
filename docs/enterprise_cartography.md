# Enterprise Cartography

AutoMap v4.0 improves Map Composer previews so proximity and parcel drafts look like county GIS review maps instead of debug diagrams. AutoMap v4.1 carries that cartography into county exhibit and staff-report-style export layouts.

The composer uses a clear draw order:

1. Basemap
2. Context polygons such as zoning, flood, and districts
3. Context lines such as roads
4. Route casing/halo
5. Route main line
6. Selected parcel outline
7. Origin marker
8. Target facility marker
9. Labels and callouts

Road-following draft routes use a moderate blue line with a white casing. Straight-line references are thinner and dashed. Route symbols are drawn below origin and target markers so the line does not cover the home or facility icon.

Proximity maps hide full address, parcel, and target-facility REST layers by default to reduce clutter. The derived origin marker, selected target marker, route/line, and selected parcel outline remain visible when truly available.

The map frame includes a concise title above the map, compact in-frame legend, north arrow, centered enterprise scale bar, and draft-only disclaimer. These are review aids only; AutoMap does not publish, upload, or create ArcGIS items from the composer preview.

The v4.2 scale bar sits bottom-center inside the map frame and spans roughly 64% of the frame width. It uses clear tick labels such as `0 0.25 0.5 mi` or `0 500 1000 ft` depending on the current view scale. The compact legend stays inside the frame but moves away from the scale bar so the distance guide reads like a county GIS exhibit element.

Preview and Print / Export share the same map-frame sizing logic. The Preview step now uses a locked, print-like frame rather than a compressed card, so the route, origin marker, target marker, legend, north arrow, and centered scale bar are visible before the user moves to print/export. Adjust is the only step where pan and zoom are enabled.

## Exhibit Layouts

v4.1 adds reusable exhibit components for a title block, map frame, staff-report notes, source table, warning summary, footer, and draft disclaimer. The print layout uses the same live composer map renderer, so the basemap, semantic symbols, route casing, in-frame legend, scale bar, and north arrow remain consistent between preview and printed staff report figures.

Generated exhibit packages stay under `outputs/exhibits/` and include HTML, JSON, CSV, warning, and manifest files. Browser print-to-PDF is the supported PDF workflow.

CFS remains separate and `cfs_dev` is not touched.
