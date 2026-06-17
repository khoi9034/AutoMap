# Route Drafts

AutoMap v3.9 supports route draft modes:

- road-following draft route when a bounded verified street centerline graph can be built safely
- straight-line reference fallback when route drafting is unavailable
- route unavailable when origin/target matching is not safe

Road-following drafts are labeled:

`Road-following draft route, not official driving directions or turn-by-turn navigation.`

Straight-line fallbacks are labeled:

`Straight-line reference only. This is not a driving route.`

AutoMap does not call paid routing APIs, external geocoding APIs, or unapproved network services.

In Map Composer previews, road-following draft routes use a moderate blue line with a white casing and are drawn under markers. Straight-line references use a thinner dashed line with a casing and a visible not-a-road-route warning.

Route draft output can include:

- matched origin summary
- matched destination summary
- road-following route draft GeoJSON when safe
- straight-line reference GeoJSON
- local Markdown/HTML report
- warning that draft routes are not official navigation
- enterprise preview styling with legend, scale bar, north arrow, and draft disclaimer

Generated route drafts are local review artifacts under `outputs/proximity/` and are ignored by Git. No ArcGIS item is created or published.

CFS remains separate and `cfs_dev` is not touched.
