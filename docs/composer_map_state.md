# Composer Map State

AutoMap v4.5 saves a canonical `composer_map_state` whenever a draft is generated, adjustments are applied, or print/export is requested. v4.7 extends that state with WYSIWYG print/export options so the print layout uses the current composer map instead of a regenerated default map.

The saved state is the source of truth for print layouts, exhibit packages, and report metadata. Print/export should not re-run recipe generation or rebuild a different map from defaults.

## Stored State

The map state records:

- composer session id
- title and subtitle
- original prompt and request type
- preview config, basemap, and map extent
- visible and hidden layers
- layer order, opacity, display titles, roles, and symbology
- derived overlays such as origin, target, selected parcel, and route/line GeoJSON
- legend items, centered scale bar config, and north arrow config
- proximity and route summaries
- parcel context
- warnings, missing data, and reviewer notes
- current center, zoom, scale, rotation, and saved extent when available
- print/export mode and WYSIWYG preservation options
- report section options and generated statistics

AutoMap stores this locally in the ignored composer session folder as `composer_map_state.json` and upserts the same object into `automap.composer_map_states` when the AutoMap database is available.

## Print/Export Rule

Preview, Adjust, Print Layout, and Exhibit outputs use the same renderer entry point and the same saved state object. If a reviewer hides a layer, changes opacity, renames a layer, changes the title, or selects Map Exhibit Only versus Full Report, print/export receives that adjusted state before generating output.

Default print/export mode is `map_exhibit_only`, which keeps the map as the first-page exhibit and leaves long tables/statistics as optional appendices. `full_report` enables appendix sections.

## Safety

The state object is local draft metadata. It does not publish ArcGIS items, does not upload local GeoJSON, does not expose secrets, and does not access the CFS database.
