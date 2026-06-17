# Route Draft Modes

AutoMap v3.8 supports explicit route draft modes for proximity maps:

- `road_network_route`: reserved for a future approved routing/network service.
- `road_following_draft`: a bounded local route approximation using verified street centerlines.
- `straight_line_reference`: a fallback reference line from origin to target.
- `route_unavailable`: no safe matched origin/target pair is available.

AutoMap does not call paid routing or geocoding APIs. When no approved routing service is configured, it tries a bounded road-following draft by querying only street centerline features inside the origin-target corridor. If the road feature count or search extent exceeds safety limits, or the local graph cannot connect the origin and target, AutoMap falls back to a straight-line reference with a visible warning.

Road-following drafts are local review artifacts only. They are not turn-by-turn driving directions, official navigation, or an emergency response route.

Route outputs remain under `outputs/proximity/` and are ignored by Git. Nothing is published to ArcGIS.

CFS remains separate and `cfs_dev` is not touched.

