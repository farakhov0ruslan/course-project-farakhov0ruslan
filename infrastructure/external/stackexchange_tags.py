from typing import List

from infrastructure.http_client import safe_http

SE_TAGS_URL = "https://api.stackexchange.com/2.3/tags"


async def fetch_popular_tags(limit: int = 20) -> List[str]:
    data = await safe_http.get_json(
        SE_TAGS_URL,
        params={
            "order": "desc",
            "sort": "popular",
            "site": "stackoverflow",
            "pagesize": min(limit, 100),
        },
    )
    items = data.get("items", [])
    names = [it["name"] for it in items if isinstance(it, dict) and "name" in it]
    return names[:limit]
