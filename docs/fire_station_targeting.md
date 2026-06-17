# Fire Station Targeting

AutoMap v3.7 handles fire station requests more conservatively.

When a user asks for the nearest fire station, AutoMap uses only verified catalog facility layers. If returned facility attributes clearly identify fire stations, AutoMap can label the target as `nearest_fire_station`.

If the verified source combines Fire and EMS stations and AutoMap cannot prove a fire-only filter, it returns:

- `target_type = nearest_fire_ems_station`
- a warning that the verified layer combines Fire and EMS stations
- a review warning when the nearest target appears EMS-related

This prevents an EMS-only record such as `EMS 2` from being silently presented as a fire station.

## Routing

Straight-line distance is supported. Road-network routing is not supported unless an approved routing/network service is added later. Route or line outputs are labeled as straight-line references, not driving routes.

## Safety

Fire/EMS searches use bounded distance rings and candidate caps. AutoMap does not download full facility datasets, does not publish outputs, and does not require ArcGIS login. CFS remains separate and untouched.
