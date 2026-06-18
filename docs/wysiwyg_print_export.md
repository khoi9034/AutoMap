# WYSIWYG Print Export

AutoMap v4.7 makes print/export use the current Map Composer state instead of rebuilding a separate map. The print layout loads the saved `composer_map_state` for the active session and renders the same map title, extent, basemap, visible layers, hidden layers, layer opacity, layer order, route style, origin/target symbols, legend, scale bar, north arrow, warnings, and reviewer notes.

## Default Mode

The default export mode is `Map Exhibit Only`.

This mode is map-first and intended to produce a one-page county GIS draft exhibit. It includes:

- title block
- exact map frame from the saved composer state
- legend
- centered scale bar
- north arrow
- short route/distance/key finding notes
- concise warnings and draft-only disclaimer

It does not force long layer/source tables, statistics, technical metadata, or appendices into the default print output.

## Other Modes

`Map + Summary` keeps the map page first and adds a short summary.

`Full Report with Appendix` adds the longer sections:

- layer source table
- warning summary
- source notes
- statistics sections
- unavailable permit/planning/development summaries when requested

These sections are optional appendices. Missing data remains explicit and is not replaced with fake counts.

## State Capture

Before adjustment, print preview, exhibit package generation, or report export, the frontend sends a snapshot of the current composer state to the backend. That snapshot records the adjusted title, subtitle, layer visibility, opacity, order, layer names, route style, symbol state, saved map extent, report options, and export mode.

The backend persists the state in:

- `outputs/composer_sessions/<composer_session_id>/composer_map_state.json`
- `automap.composer_map_states`

## Safety

Print/export outputs are local draft artifacts only. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not upload local GeoJSON, does not bulk-download datasets, and does not touch the CFS database.
