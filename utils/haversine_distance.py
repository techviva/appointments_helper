import math

BASE_LAT, BASE_LON = 33.57616, -112.12666  # 10000 N 31st Ave, Phoenix, AZ 85051
AVG_MPH = 32  # conservative metro average (tweakable)

def haversine_miles(a_lat, a_lon, b_lat=BASE_LAT, b_lon=BASE_LON):
    R = 3958.7613  # miles
    dlat = math.radians(a_lat - b_lat)
    dlon = math.radians(a_lon - b_lon)
    lat1, lat2 = map(math.radians, (b_lat, a_lat))
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def estimate_minutes_from_base(lat, lon, avg_mph: float = AVG_MPH) -> int:
    miles = haversine_miles(lat, lon)
    return round((miles / avg_mph) * 60)
