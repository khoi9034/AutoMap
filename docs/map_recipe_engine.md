# AutoMap Map Recipe Engine

AutoMap v0.2 converts plain-English GIS requests into structured map recipes using only verified records from `automap.layer_catalog`.

## Prompt Parser

The parser extracts:

- raw prompt text
- geography terms such as Concord, Kannapolis, Harrisburg, ETJ, municipal limits, and countywide
- topics such as parcels, zoning, floodplain, school districts, roads, permits, addresses, hydrology, contours, voting, and facilities
- time references such as current, recent, historical, archive, and specific years from 2010 through 2015
- requested output type
- analysis intent such as display, filter, proximity, or overlay/intersection

## Layer Matcher

The matcher reads trusted metadata from `automap.layer_catalog`. It searches layer names, service names, category, aliases, description, planning use cases, canonical topic, source status, and historical year.

Scoring prefers:

- exact topic aliases, category matches, and layer name matches
- verified REST layers
- new separated OpenData services with priority `1`
- feature layers over group layers
- historical layers only when the prompt asks for history or a specific year

Legacy layers remain available as fallback/historical metadata, but verified new OpenData layers are preferred for current requests.

## Recipe Output

Recipes include selected layers, rejected lower-scoring layers, filters, spatial operations, symbology recommendations, suggested extent, confidence, review flags, and missing data notes.

AutoMap does not invent layer names, URLs, fields, or data sources. If a requested topic is not in the verified catalog, it appears in `missing_data_needed`.

## Safety Boundaries

- No feature geometries are downloaded.
- No full datasets are ingested.
- No ArcGIS web maps are created yet.
- No external LLM API is used.
- CFS is separate and was not touched.
- AutoMap refuses the protected `cfs_dev` database name.

## Example

```bash
python -m app.main --make-recipe "Show parcels in Concord that are in the 100-year floodplain."
```

Optional local save:

```bash
python -m app.main --make-recipe "Show school districts for parcels in Harrisburg." --save-recipe
```

