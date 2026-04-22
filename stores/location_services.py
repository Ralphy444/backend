import json
import os
from math import radians, sin, cos, sqrt, atan2
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db.models import Q

from .models import SavedLocation

DEFAULT_CENTER = {'lat': 10.3157, 'lng': 123.8854}
DELIVERY_ZONE_NAME = 'Cebu Core Zone'
DELIVERY_ZONE_POLYGON = [
    (10.3600, 123.8600),
    (10.3600, 123.9200),
    (10.2800, 123.9200),
    (10.2800, 123.8600),
]


def point_in_polygon(lat, lng, polygon):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > lng) != (yj > lng)) and (
            lat < (xj - xi) * (lng - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def zone_status(lat, lng):
    if lat is None or lng is None:
        return {'in_zone': None, 'zone_name': ''}
    in_zone = point_in_polygon(lat, lng, DELIVERY_ZONE_POLYGON)
    return {'in_zone': in_zone, 'zone_name': DELIVERY_ZONE_NAME if in_zone else ''}


def build_navigation_links(lat, lng):
    if lat is None or lng is None:
        return {}
    coords = f'{lat},{lng}'
    return {
        'google_maps': f'https://www.google.com/maps/dir/?api=1&destination={coords}&travelmode=driving',
        'waze': f'waze://?ll={coords}&navigate=yes',
        'apple_maps': f'http://maps.apple.com/?daddr={coords}&dirflg=d',
    }


def haversine_distance_m(lat1, lng1, lat2, lng2):
    earth_radius_m = 6371000
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * earth_radius_m * atan2(sqrt(a), sqrt(1 - a))


def _request_json(url, headers=None, timeout=4):
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def search_saved_locations(query, lat=None, lng=None, limit=5):
    filters = Q(is_public=True)
    if query:
        filters &= Q(search_text__icontains=query)

    candidates = list(SavedLocation.objects.filter(filters)[:50])
    ranked = []
    for item in candidates:
        score = item.usage_count * 5
        if query:
            haystack = (item.search_text or '').lower()
            if query.lower() in haystack:
                score += 25
        if lat is not None and lng is not None:
            distance = haversine_distance_m(lat, lng, item.latitude, item.longitude)
            score += max(0, 1500 - distance) / 100
            distance_m = round(distance)
        else:
            distance_m = None
        ranked.append((score, distance_m, item))

    ranked.sort(key=lambda row: row[0], reverse=True)
    results = []
    for _, distance_m, item in ranked[:limit]:
        results.append({
            'source': 'user_submitted',
            'title': item.label or item.address.split(',')[0],
            'address': item.address,
            'lat': item.latitude,
            'lng': item.longitude,
            'notes': item.notes,
            'landmarks': item.landmarks,
            'distance_m': distance_m,
            'source_details': item.source_details,
        })
    return results


def search_osm_locations(query, limit=6):
    if not query:
        return []
    params = urlencode({
        'q': query,
        'format': 'json',
        'addressdetails': 1,
        'limit': limit,
        'countrycodes': 'ph',
        'viewbox': '123.75,10.45,124.05,10.15',
        'bounded': 0,
    })
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    try:
        payload = _request_json(url, headers={'Accept-Language': 'en', 'User-Agent': 'FoodOrderingApp/1.0'})
    except Exception:
        return []

    results = []
    for item in payload:
        display_name = item.get('display_name', '')
        results.append({
            'source': 'openstreetmap',
            'title': display_name.split(',')[0].strip() if display_name else query,
            'address': display_name,
            'lat': float(item['lat']),
            'lng': float(item['lon']),
            'notes': '',
            'landmarks': [],
            'source_details': {
                'osm_type': item.get('osm_type'),
                'osm_id': item.get('osm_id'),
            },
        })
    return results


def search_google_locations(query, limit=4):
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '') or os.getenv('GOOGLE_MAPS_API_KEY', '')
    if not query or not api_key:
        return []

    params = urlencode({
        'query': query,
        'key': api_key,
        'region': 'ph',
    })
    url = f'https://maps.googleapis.com/maps/api/place/textsearch/json?{params}'
    try:
        payload = _request_json(url)
    except Exception:
        return []

    results = []
    for item in payload.get('results', [])[:limit]:
        location = item.get('geometry', {}).get('location', {})
        lat = location.get('lat')
        lng = location.get('lng')
        if lat is None or lng is None:
            continue
        results.append({
            'source': 'google_maps',
            'title': item.get('name') or item.get('formatted_address', query),
            'address': item.get('formatted_address') or item.get('name', query),
            'lat': float(lat),
            'lng': float(lng),
            'notes': '',
            'landmarks': [],
            'source_details': {
                'place_id': item.get('place_id'),
                'rating': item.get('rating'),
                'types': item.get('types', []),
            },
        })
    return results


def merge_location_results(*groups, limit=10):
    seen = set()
    merged = []
    for group in groups:
        for result in group:
            key = (round(result['lat'], 5), round(result['lng'], 5), result.get('title', '').lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append(result)
            if len(merged) >= limit:
                return merged
    return merged
