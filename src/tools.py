import functools

import requests

QUERY_URL = "https://api.github.com/search/code?q=repo:r-anime/comment-face-assets+path:/source+filename:"
QUERY_URL_SEASONAL = "https://api.github.com/search/code?q=repo:r-anime/comment-face-assets+path:/source_seasonal_faces+sort:updated-desc+filename:"
ASSET_URL = "https://raw.githubusercontent.com/r-anime/comment-face-assets/master/"
SEASONAL_PREFIX = "seasonal"
DEFAULT_TIMEOUT = 60


@functools.cache
def get_url(commentface: str) -> str:
    """Return the URL matching the commentface code."""
    seasonal = commentface.startswith(SEASONAL_PREFIX)
    if seasonal:
        commentface = commentface[len(SEASONAL_PREFIX) :]
        r = requests.get(
            f"{QUERY_URL_SEASONAL}{commentface.lower()}", timeout=DEFAULT_TIMEOUT
        )
    else:
        r = requests.get(f"{QUERY_URL}{commentface.lower()}", timeout=DEFAULT_TIMEOUT)
    if r.status_code == 200:
        data = r.json()
        if data["items"]:
            for item in data["items"]:
                if "/original/" in item["path"]:
                    url = f'{ASSET_URL}{item["path"]}'.replace(" ", "%20")
                    if requests.get(url, timeout=DEFAULT_TIMEOUT).status_code == 200:
                        return url
    return ""
