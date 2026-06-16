# Proximity and Nearest Facility Workflows

AutoMap v3.1 adds draft proximity workflows for parcel/address origins and verified catalog destination layers.

Supported local outputs:

- nearest straight-line distance
- origin parcel/address to nearest facility
- containing district context for fire and school districts
- local GeoJSON straight-line output
- local Markdown/HTML/JSON report files under `outputs/proximity/`

Safety rules:

- origin matching uses `returnGeometry=false` first
- target searches use bounded distance rings
- candidate feature downloads are capped
- countywide feature datasets are not downloaded
- outputs are draft GIS review files only
- nothing is published to ArcGIS Online, Enterprise, or Portal

Target examples:

- nearest school
- nearest elementary, middle, or high school
- nearest fire/EMS station
- containing fire district
- nearest library or county facility
- nearest polling place

Fire district wording matters. If the user asks what district a parcel is in, AutoMap treats that as polygon containment. If the user asks for nearest fire station, AutoMap uses station point layers when verified.

CFS remains separate. AutoMap does not connect to or modify `cfs_dev`.
