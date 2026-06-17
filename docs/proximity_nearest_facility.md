# Proximity and Nearest Facility Workflows

AutoMap v3.1 adds draft proximity workflows for parcel/address origins and verified catalog destination layers.

AutoMap v3.5 routes address prompts such as `my address 793 bartram ave ... nearest fire station` directly into proximity handling. The address is treated only as a user-supplied origin.

Supported local outputs:

- nearest straight-line distance
- origin parcel/address to nearest facility
- containing district context for fire and school districts
- local GeoJSON origin point, target feature, and straight-line output
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

Road-network routing is not implied by a line request. Unless an approved routing/network service exists, AutoMap labels the output as a straight-line reference, not a driving route.

In the Map Composer, v3.6 renders the local proximity GeoJSON outputs as focused overlays. The map extent is fit to the origin, target, and line with a buffer. If the origin address is matched but a related parcel is not resolved, AutoMap shows the address point and line and warns that no selected parcel outline is available.

CFS remains separate. AutoMap does not connect to or modify `cfs_dev`.
