import json
from typing import List, Optional
import requests

from .base_search_provider import BaseSearchProvider, SearchHit
from .config import METASO_API_KEY, METASO_BASE_URL

class MetasoSearchProvider(BaseSearchProvider):
    name = "metaso"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "fast", fmt: str = "simple"):
        self._api_key = api_key or METASO_API_KEY
        if not self._api_key:
            raise ValueError("METASO_API_KEY is required for MetasoSearchProvider")
        self._base_url = base_url or METASO_BASE_URL
        self._model = model
        self._format = fmt

    def search(
        self,
        query: str,
        *,
        count: int = 5,  # Metaso 不支持 count 的链接列表，这里仅兼容签名
        category: Optional[str] = None,
        recency_filter: str = "noLimit",
        content_size: str = "medium",
        intent: bool = True,
    ) -> List[SearchHit]:
        payload = {"q": query, "model": self._model, "format": self._format}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        r = requests.post(self._base_url, headers=headers, data=json.dumps(payload), timeout=30)
        r.raise_for_status()
        data = r.json()
        # Metaso 返回的是 answer 文本，不含链接。映射为一个 SearchHit（无 url）
        answer = data.get("answer")
        title = data.get("title") or "Metaso Answer"
        if isinstance(answer, str):
            return [SearchHit(url=None, title=title, snippet=answer, provider=self.name, raw=data)]
        # 如果结构不同，确保至少返回一个 raw
        return [SearchHit(url=None, title=title, snippet=json.dumps(data, ensure_ascii=False), provider=self.name, raw=data)]
