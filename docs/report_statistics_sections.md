# Report Statistics Sections

AutoMap v4.5 adds configurable report sections for Map Composer print/export. AutoMap v4.6 adds optional table preview and table export summary sections for map+table requests.

## Available Sections

The Print / Export step can include:

- map summary
- selected layer table
- warnings and limitations
- source notes
- proximity and distance summary
- parcel summary when available
- table preview when available
- table export summary when available
- statistics section
- permit, planning, and development proxy sections when verified data is available

## Current Statistics

The first statistics builder reports safe metadata only:

- visible layer count
- hidden layer count
- derived overlay count
- warning count
- missing data count
- source role counts for official, proxy, reference, and derived local layers
- route distance and route mode for proximity maps
- origin and target names when available
- parcel match status and selected parcel count when available
- table estimated row count, field count, source layer count, safety status, export status, and `returnGeometry=false` setting when available

Permit, planning case, and development proxy statistics are explicit placeholders until verified bounded sources support those summaries. AutoMap marks them `available: false` with a reason instead of inventing counts.

## Draft Status

Statistics sections are for GIS review. They are not official planning decisions, permit totals, or development approvals. Proxy sources remain labeled as context only.
