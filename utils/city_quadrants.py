from shapely.geometry import shape, Point
import json
from pathlib import Path

# zones.geojson: FeatureCollection; each Feature has properties: {"name": "...", "label": "close|high_traffic|medium|east_special"}
ZONES_PATH = Path("config/zones.geojson")

with ZONES_PATH.open() as f:
    _zones = json.load(f)["features"]

# Build (label, polygon) list once
ZONE_POLYGONS = [(feat["properties"]["label"], shape(feat["geometry"])) for feat in _zones]

def classify_zone(lat: float, lon: float) -> str:
    p = Point(lon, lat)  # NOTE: (x=lon, y=lat)
    for label, poly in ZONE_POLYGONS:
        if poly.contains(p) or poly.touches(p):
            return label
    return "unclassified"
