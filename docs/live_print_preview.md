# Live Print Preview

AutoMap v4.8 adds a live Print / Export preview panel to Map Composer.

The Print / Export step uses two columns:

- left: export mode, report section checkboxes, local export buttons, and locked-map status
- right: a scrollable page preview showing the final print document

The preview updates immediately when a section checkbox changes. It uses the locked final composer map state, including the adjusted title, extent, basemap, visible layers, hidden layers, layer order, opacity, route line, origin and target symbols, legend, scale bar, north arrow, warnings, and reviewer notes.

## Locked Map State

Print/export does not re-run the prompt or regenerate the recipe. The frontend captures the current composer state and sends it to the backend before browser print or exhibit package generation.

If the reviewer returns to Adjust, the map can be edited again and re-locked by applying adjustments.

## Browser Print

`Open Browser Print` opens the print layout for the current session. Print CSS hides the app shell, sidebar, buttons, and debug panels so only the selected print document pages are printed.

The default mode is `Map only`, which keeps the first output map-focused. Optional report sections and appendices appear only when selected.

## Safety

Live preview and print/export outputs are local draft artifacts. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not bulk-download datasets, and does not touch CFS.
