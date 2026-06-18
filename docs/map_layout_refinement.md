# Map Layout Refinement

AutoMap v4.0 refines the Map Composer preview into a cleaner county GIS draft map composition.

Map furniture placement:

- title and subtitle sit above the map frame
- north arrow sits inside the top-right of the map frame
- adaptive scale bar sits inside the bottom-left of the map frame
- compact legend sits inside the bottom-right of the map frame
- route lines draw below selected parcel, origin, and target symbols

The legend shows only visible, relevant layers. Hidden full address, parcel, and target-facility REST layers are not included in the legend unless the user explicitly enables them.

The scale bar is labeled in local imperial units. Depending on the map scale, it shows feet or miles with labels such as `0 500 1000 ft` or `0 0.25 0.5 mi`.

The preview remains local and draft-only. AutoMap does not publish, upload, or create ArcGIS items from the composer preview.

CFS remains separate and `cfs_dev` is not touched.
