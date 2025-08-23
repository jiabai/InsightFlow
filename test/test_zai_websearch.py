from typing import List, Optional, Any, cast
from dataclasses import dataclass

from zai import ZhipuAiClient
from zai.types.web_search import SearchResultResp, WebSearchResp

@dataclass
class SearchHit:
    url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    provider: str
    score: Optional[float] = None
    published_at: Optional[str] = None
    raw: Optional[Any] = None  # 保留原始返回，便于定位问题

client = ZhipuAiClient(api_key="")

response: WebSearchResp = client.web_search.web_search(
   search_engine="search_pro",
   search_query="特朗普关税政策",
   search_intent=True,
   count=1,  # 返回结果的条数，范围1-50，默认10
   search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
   content_size="medium"  # 控制网页摘要的字数，默认medium
)

hits: List[SearchHit] = []
name = "zhipu"
sr = getattr(response, "search_result", None)

def _to_hit(item: Any) -> Optional[SearchHit]:
    # 适配 Zhipu SDK 对象或 dict
    try:
        if isinstance(item, SearchResultResp):
            url = getattr(item, "link", None)
            title = getattr(item, "title", None) if hasattr(item, "title") else None
            snippet = getattr(item, "abstract", None) if hasattr(item, "abstract") else None
            score = getattr(item, "score", None) if hasattr(item, "score") else None
            published_at = getattr(item, "publish_time", None) if hasattr(item, "publish_time") else None
            return SearchHit(url=url, title=title, snippet=snippet, provider=name,
                                score=score, published_at=published_at, raw=item)
        elif isinstance(item, dict):
            url = cast(Optional[str], item.get("link"))
            title = cast(Optional[str], item.get("title"))
            snippet = cast(Optional[str], item.get("abstract") or item.get("summary"))
            score = item.get("score")
            published_at = cast(Optional[str], item.get("publish_time") or item.get("date"))
            return SearchHit(url=url, title=title, snippet=snippet, provider=name,
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

# print(hits)

seen_urls = set()
seen_snippets = set()
deduped: List[SearchHit] = []
for h in hits:
    key_url = (h.url or "").strip()
    key_snip = (h.provider, (h.snippet or "").strip())
    if key_url:
        if key_url in seen_urls:
            continue
        seen_urls.add(key_url)
    else:
        if key_snip in seen_snippets:
            continue
        seen_snippets.add(key_snip)
    deduped.append(h)

if deduped:
    print(f"hits: {len(deduped)}; urls: {[h.url for h in deduped if h.url]}")

# deduped_list = [asdict(h) for h in deduped]
# print(deduped_list)


# if hasattr(response, 'search_result') and isinstance(response.search_result, list):
#     for result in response.search_result:
#         print(result.link)
# else:
#     print("No search results found in response")
