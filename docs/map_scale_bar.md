# Map Scale Bar

AutoMap v4.2 uses a centered enterprise-style scale bar in Map Composer previews and print/exhibit layouts.

## Placement

The scale bar sits inside the map frame at the bottom center. It spans about 64% of the map frame width, with responsive limits so it stays readable on smaller screens and in print.

Recommended map furniture placement:

- title and subtitle above the map frame
- north arrow inside the top-right of the map frame
- compact legend inside the upper-right of the map frame
- centered scale bar inside the bottom-center of the map frame

The legend is kept away from the scale bar so the distance guide remains readable.

## Labels

The scale bar uses imperial units for county map review:

- feet for tighter extents
- miles for larger extents

Labels use clear tick marks:

```text
0        0.25        0.5 mi
0        500         1000 ft
```

The bar does not use vague-only labels such as `approx.`. Labels are derived from the ArcGIS MapView scale and snapped to readable distances.

## Draft Status

The scale bar is a review aid for local draft maps and exhibit exports. It does not make the output an official survey, official navigation, or official county map.

CFS remains separate and untouched.
