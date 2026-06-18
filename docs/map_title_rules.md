# Map Title Rules

AutoMap v4.0 generates short, readable Map Composer titles instead of exposing internal layer names.

Rules:

- use the request type and map focus
- avoid generic layer names such as `Addresses` or `Tax Parcels`
- keep titles concise enough for a print layout
- use subtitles for route mode or draft status, not long explanations

Examples:

- `Nearest Fire Station from 793 Bartram Ave`
- `Parcels in Concord Floodplain`
- `Commercial Zoning Around Concord`
- `School Districts for Harrisburg Parcels`

Subtitles stay subtle:

- `Road-following draft route.`
- `Straight-line reference only.`
- `Draft preview only.`

Titles and subtitles are deterministic and local. No external AI or paid service is used.

CFS remains separate and `cfs_dev` is not touched.
