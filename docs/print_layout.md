# Print Layout

AutoMap v4.0 adds a print-oriented Map Composer layout for local draft review.

The print page includes:

- map title and subtitle
- the focused composer map preview
- compact legend in or adjacent to the map composition
- labeled scale bar using miles or feet
- north arrow
- original prompt
- route and distance summary when applicable
- selected/visible layers
- warnings and missing data notes
- generated date/time
- draft-only disclaimer

Print output is local and review-only. It is not an official county map, not official navigation, and not a real ArcGIS publish action.

Route labels remain explicit:

- road-following draft route: bounded local centerline approximation, not turn-by-turn driving directions
- straight-line reference: fallback line only, not a road route

Generated print/report outputs stay in ignored output folders and should not be committed.

CFS remains separate and `cfs_dev` is not touched.
