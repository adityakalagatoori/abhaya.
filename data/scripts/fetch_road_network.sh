#!/bin/bash
# Fetch real OSM road network for Surat, Gujarat via Overpass API
set -e
OUT="../road_network/surat_roads_raw.geojson"
curl -s -X POST "https://overpass-api.de/api/interpreter" --data-urlencode 'data=
[out:json][timeout:180];
area["name"="Surat"]["boundary"="administrative"]->.a;
(
  way["highway"](area.a);
);
out body geom;
' -o "../road_network/surat_roads_overpass.json"
echo "Downloaded overpass raw JSON:"
ls -la ../road_network/
