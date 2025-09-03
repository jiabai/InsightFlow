from dataclasses import dataclass
from typing import Any, List, Optional

@dataclass
class SearchHit:
    url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    provider: str
    score: Optional[float] = None
    published_at: Optional[str] = None
    raw: Optional[Any] = None  # 保留原始返回，便于定位问题

class BaseSearchProvider:
    name: str = "base"

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
        raise NotImplementedError
