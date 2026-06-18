# WYSIWYG Print Export

AutoMap v4.7 made print/export use the current Map Composer state instead of rebuilding a separate map. AutoMap v4.8 adds a live Print / Export preview panel so users can choose report sections and immediately see the final page layout. The print layout loads the saved `composer_map_state` for the active session and renders the same map title, extent, basemap, visible layers, hidden layers, layer opacity, layer order, route style, origin/target symbols, legend, scale bar, north arrow, warnings, and reviewer notes.

## Default Mode

The default export mode is `Map only`.

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

`Map + summary` keeps the map page first and adds a short summary.

`Full report` adds longer sections by default:

- layer source table
- warning summary
- source notes
- statistics sections
- unavailable permit/planning/development summaries when requested

These sections are optional appendices. Missing data remains explicit and is not replaced with fake counts.

## State Capture

Before adjustment, print preview, exhibit package generation, or report export, the frontend sends a snapshot of the current composer state to the backend. That snapshot records the adjusted title, subtitle, layer visibility, opacity, order, layer names, route style, symbol state, saved map extent, report options, and export mode.

In v4.8, section checkbox choices are also stored as print/export options. The live preview and browser print route use the same print document component so the visible preview and printed pages stay aligned.

The backend persists the state in:

- `outputs/composer_sessions/<composer_session_id>/composer_map_state.json`
- `automap.composer_map_states`

## Safety

Print/export outputs are local draft artifacts only. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not upload local GeoJSON, does not bulk-download datasets, and does not touch the CFS database.
