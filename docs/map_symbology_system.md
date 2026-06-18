# Map Symbology System

AutoMap v4.0 uses semantic symbols and enterprise cartographic ordering for Map Composer preview overlays.

Derived overlay metadata includes `symbol_key`, `geometry_role`, `route_mode`, `route_label`, `facility_type`, and `default_visible`. The frontend uses these keys to render a consistent ArcGIS preview:

- `origin_home` / `origin_address`: home marker for the user-supplied origin.
- `target_fire_station`: fire/facility marker for verified fire station targets.
- `target_school`: school marker.
- `target_hospital`: hospital/medical marker.
- `target_park`: park marker.
- `target_library`: library marker.
- `target_polling_place`: polling place marker.
- `target_facility`: generic facility marker.
- `route_road_following`: moderate solid road-following draft line with white casing.
- `route_straight_line`: thinner dashed straight-line reference with white casing.
- `selected_parcel`: transparent parcel fill with highlighted outline.

Full REST context layers are not the same as derived result overlays. For proximity maps, AutoMap hides full address, parcel, and target-facility layers by default to reduce clutter. The origin marker, nearest target marker, route/line, and selected parcel overlay remain visible.

Draw order is intentional: route casing and route line draw below selected parcels and below origin/target markers. Markers stay visually on top of route lines.

The map legend only includes visible layers. Hidden address and parcel context layers are listed as hidden context in the layer panel, not as active legend items.

Symbols are preview-only local styling. They do not publish, upload, or create ArcGIS items.

CFS remains separate and `cfs_dev` is not touched.
