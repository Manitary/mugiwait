from functools import cache
import requests

QUERY_URL = "https://api.github.com/search/code?q=repo:r-anime/comment-face-assets+path:/source+filename:"
QUERY_URL_SEASONAL = "https://api.github.com/search/code?q=repo:r-anime/comment-face-assets+path:/source_seasonal_faces+sort:updated-desc+filename:"
ASSET_URL = "https://raw.githubusercontent.com/r-anime/comment-face-assets/master/"
SEASONAL_PREFIX = "seasonal"

@cache
def getURL(text: str):
    seasonal = text.startswith(SEASONAL_PREFIX)
    if seasonal:
        text = text[len(SEASONAL_PREFIX):]
        r = requests.get(f"{QUERY_URL_SEASONAL}{text.lower()}")
    else:
        r = requests.get(f"{QUERY_URL}{text.lower()}")
    if r.status_code == 200:
        data = r.json()
        if data["items"]:
            for item in data["items"]:
                if "/original/" in item["path"]:
                    url = f'{ASSET_URL}{item["path"]}'.replace(' ', '%20')
                    if requests.get(url).status_code == 200:
                        return url
    return