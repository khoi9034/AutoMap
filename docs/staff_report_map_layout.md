# Staff Report Map Layout

AutoMap v4.1 adds a print-oriented staff report exhibit layout for Map Composer sessions.

AutoMap v4.5 renders print/report output from the saved composer map state. The print page should show the same map title, extent, basemap, visible layers, hidden layers, opacity, order, route/line styling, symbols, legend, scale bar, north arrow, warnings, and notes that the reviewer had in the Composer.

## Layout Structure

The print layout includes:

- concise map title
- subtitle or purpose
- original prompt
- prepared by `AutoMap Draft`
- generated date/time
- draft status badge
- map type and request type
- composer session id
- live map frame
- legend, scale bar, and north arrow from the composer map frame
- key findings or map notes
- layer source table
- warning and limitation summary
- optional report/statistics sections
- draft-only disclaimer

The normal app sidebar and buttons are hidden when printing.

## Staff Report Mode

For proximity maps, key findings include:

- origin
- nearest target
- distance
- route mode
- related parcel status

For parcel, flood, zoning, scenario, and general reference maps, the layout summarizes preview status, selected layers, request type, data limitations, and warnings.

## Print Workflow

Open the layout from Map Composer:

```text
Open Print Layout
```

Or use:

```text
/map-composer/<composer_session_id>/print
/print/<composer_session_id>
```

Browser print-to-PDF is the supported PDF path for v4.1. The print layout uses landscape page behavior, keeps the map frame together, and keeps the source table and warnings readable.

The print route loads the saved composer session and `composer_map_state`. It does not re-run recipe generation or silently replace the adjusted map with a default map.

## Draft Status

Staff report maps are draft GIS review figures. They are not official county maps, not official navigation, and not publication artifacts. Proxy layers remain labeled as context, selected parcel outlines only appear when truly resolved, and local derived outputs are not uploaded.

CFS remains separate and untouched.
