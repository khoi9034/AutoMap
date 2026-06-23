# AutoMap Portfolio Demo Script

Use this as a two-minute walkthrough for recruiters, GIS teams, or planning employers.

## 1. Open The Homepage

Open https://auto-map-cyan.vercel.app.

Say: "AutoMap is a county GIS request engine. It converts plain-language planning questions into draft maps, tables, and review-ready outputs."

## 2. Explain The Scope

Point out the scope badge.

Say: "The live demo is intentionally scoped to Cabarrus County, North Carolina. It is not a nationwide geocoder."

## 3. Open Map Composer

Click **Open Live Demo**.

Say: "The public UI uses a live backend first. If the free backend is warming up, it can fall back to a static demo without looking broken."

## 4. Run The Nearest Fire Station Preset

Choose **Nearest Fire Station Route** and click **Generate Draft Map**.

Expected result:

- Address match for 793 Bartram Ave
- Nearest fire station target
- Road-network route when centerlines are available
- Draft-only route warning

Say: "This uses verified county address/facility data and a bounded road-following draft. It is not official navigation."

## 5. Show Print / Export

Open **Print / Export** after the map is ready.

Say: "The print preview preserves the composer map state and keeps real ArcGIS publishing disabled."

## 6. Show A Second Preset

Use either:

- **Floodplain Parcel Screening** for a map-focused planning example
- **Parcel Table Request** for a table-preview/export-safety example

Say: "Table requests use `returnGeometry=false`, selected verified fields, and safe row/export limits."

## 7. Close With Safety

Say: "AutoMap is built as a draft GIS review assistant. It avoids owner/name lookup by default, does not use paid geocoding, and does not publish real ArcGIS items from the public UI."
