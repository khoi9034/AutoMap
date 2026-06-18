# Composer Map State

AutoMap v4.5 saves a canonical `composer_map_state` whenever a draft is generated, adjustments are applied, or print/export is requested.

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
- report section options and generated statistics

AutoMap stores this locally in the ignored composer session folder as `composer_map_state.json` and upserts the same object into `automap.composer_map_states` when the AutoMap database is available.

## Print/Export Rule

Preview, Adjust, Print Layout, and Exhibit outputs use the same renderer entry point and the same saved state object. If a reviewer hides a layer, changes opacity, renames a layer, or changes the title, print/export receives that adjusted state before generating output.

## Safety

The state object is local draft metadata. It does not publish ArcGIS items, does not upload local GeoJSON, does not expose secrets, and does not access the CFS database.
