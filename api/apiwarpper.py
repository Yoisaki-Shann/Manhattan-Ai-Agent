
import json
import time
import config

_cache: dict = {}

# Headers
def _get_headers() -> dict:
    headers = {"User-Agent": "manhattan-bot"}
    if config.UMAMOE_API_KEY:
        headers["X-API-Key"] = config.UMAMOE_API_KEY
    return headers

# get json from a URL with caching
def _get_json(url: str):
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < config.CACHE_SECONDS:
        return hit[1]
    import httpx  
    r = httpx.get(url, timeout=15, headers=_get_headers())
    r.raise_for_status()
    data = r.json()
    _cache[url] = (time.time(), data)
    return data

# get circle data
def get_circle(circle_id, year: int = None, month: int = None) -> dict:
    if not config.UMAMOE_CIRCLE_URL:
        raise RuntimeError("UMAMOE_CIRCLE_URL is not set in .env")
    url = config.UMAMOE_CIRCLE_URL.format(circle_id=circle_id)
    # Only append year/month if explicitly provided — empty values cause 400
    if year:
        url += f"&year={year}"
    if month:
        url += f"&month={month}"
    return _get_json(url)

# get user data
def get_user(viewer_id) -> dict:
    if not config.UMAMOE_USER_URL:
        raise RuntimeError("UMAMOE_USER_URL is not set in .env")
    url = config.UMAMOE_USER_URL.format(viewer_id=viewer_id)
    return _get_json(url)
