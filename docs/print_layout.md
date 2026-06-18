# Print Layout

AutoMap v4.0 adds a print-oriented Map Composer layout for local draft review. AutoMap v4.1 upgrades that print page into a staff-report-style county exhibit layout. AutoMap v4.7 makes print/export WYSIWYG: the print page uses the saved current `composer_map_state` and does not regenerate a separate map. AutoMap v4.8 adds a live Print / Export preview panel with optional report sections.

The print page includes:

- map title and subtitle
- the focused composer map preview
- compact legend in or adjacent to the map composition
- centered enterprise scale bar using miles or feet
- north arrow
- original prompt
- route and distance summary when applicable
- selected/visible layers through the saved layer state
- concise warnings and missing data notes
- generated date/time
- draft-only disclaimer
- optional layer source table
- optional source notes
- optional staff-report key findings and statistics

Print output is local and review-only. It is not an official county map, not official navigation, and not a real ArcGIS publish action.

Route labels remain explicit:

- road-following draft route: bounded local centerline approximation, not turn-by-turn driving directions
- straight-line reference: fallback line only, not a road route

Generated print/report outputs stay in ignored output folders and should not be committed.

Map Composer now exposes `Open Browser Print` for the browser-print exhibit page and `Generate Exhibit Package` for local files under `outputs/exhibits/`. The local package includes `exhibit.html`, `exhibit_data.json`, `layer_sources.csv`, `warnings.json`, and `export_manifest.json`.

Default export mode is `Map only`, a map-first output. `Map + summary` and `Full report` are available when the user wants source tables, warnings, source notes, and statistics. Appendix tables are not forced into the default print and can be previewed live before printing.

v4.2 keeps the scale bar bottom-center inside the map frame, spanning about 64% of the frame width. The scale bar stays readable in print and uses real tick labels such as `0 0.25 0.5 mi` or `0 500 1000 ft`. The legend remains in-frame but avoids the scale bar.

CFS remains separate and `cfs_dev` is not touched.
