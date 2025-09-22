from typing import Any, List, Optional, cast

from zai import ZhipuAiClient
from zai.types.web_search import SearchResultResp

from .config import ZAI_API_TOKEN
from .base_search_provider import BaseSearchProvider, SearchHit

class ZhipuSearchProvider(BaseSearchProvider):
    name = "zhipu"

    # 可按需要将不同 category 映射为不同引擎
    ENGINE_MAP = {
        "news": "search_pro",
        "company": "search_pro",
        "research paper": "search_pro",
        "github": "search_pro",
        "financial report": "search_pro",
        None: "search_pro",
    }

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or ZAI_API_TOKEN
        if not self._api_key:
            raise ValueError("ZHIPU_API_KEY is required for ZhipuSearchProvider")
        self._client = ZhipuAiClient(api_key=self._api_key)

    def search(
        self,
        query: str,
        *,
        count: int = 5,
        category: Optional[str] = None,
        recency_filter: str = "noLimit",
        content_size: str = "medium",
        intent: bool = True,
    ) -> List[SearchHit]:
        engine = self.ENGINE_MAP.get(category, self.ENGINE_MAP[None])
        resp = self._client.web_search.web_search(
            search_engine=engine,
            search_query=query,
            search_intent=intent,
            count=count,
            search_recency_filter=recency_filter,
            content_size=content_size,
        )

        hits: List[SearchHit] = []
        sr = getattr(resp, "search_result", None)

        def _to_hit(item: Any) -> Optional[SearchHit]:
            # 适配 Zhipu SDK 对象或 dict
            try:
                if isinstance(item, SearchResultResp):
                    url = getattr(item, "link", None)
                    title = getattr(item, "title", None) if hasattr(item, "title") else None
                    snippet = getattr(item, "abstract", None) if hasattr(item, "abstract") else None
                    score = getattr(item, "score", None) if hasattr(item, "score") else None
                    published_at = getattr(item, "publish_time", None) if hasattr(item, "publish_time") else None
                    return SearchHit(url=url, title=title, snippet=snippet, provider=self.name,
                                     score=score, published_at=published_at, raw=item)
                elif isinstance(item, dict):
                    url = cast(Optional[str], item.get("link"))
                    title = cast(Optional[str], item.get("title"))
                    snippet = cast(Optional[str], item.get("abstract") or item.get("summary"))
                    score = item.get("score")
                    published_at = cast(Optional[str], item.get("publish_time") or item.get("date"))
                    return SearchHit(url=url, title=title, snippet=snippet, provider=self.name,
                                     score=score, published_at=published_at, raw=item)
            except Exception:
                return None
            return None

        if isinstance(sr, list):
            for it in sr:
                hit = _to_hit(it)
                if hit:
                    hits.append(hit)
        elif isinstance(sr, SearchResultResp):
            hit = _to_hit(sr)
            if hit:
                hits.append(hit)
        elif isinstance(sr, dict):
            hit = _to_hit(sr)
            if hit:
                hits.append(hit)

        return hits
