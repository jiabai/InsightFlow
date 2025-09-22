import os
import json
import asyncio
import time
from typing import Optional, Any, List, Dict, Iterable, Set

from ai_sdk import tool

from .schemas import ArticleContent
from .resilient_crawl import resilient_extract
from .config import ZAI_PROVIDER, ZAI_API_TOKEN, ZAI_MODEL_URL

from .zhipu_search_provider import ZhipuSearchProvider
from .metaso_search_provider import MetasoSearchProvider
from .base_search_provider import BaseSearchProvider, SearchHit

MAX_TITLE_CHARS = int(os.getenv("WEBSEARCH_MAX_TITLE", "80"))
MAX_SNIPPET_CHARS = int(os.getenv("WEBSEARCH_MAX_SNIPPET", "250"))
TOP_K_HITS = int(os.getenv("WEBSEARCH_TOPK", "2"))

INSTRUCTION = """请从网页内容中提取核心信息，具体要求：
    1. 提取文章标题和副标题
    2. 提取正文的主要段落内容
    3. 保留重要的数据、引用和关键事实
    4. 过滤掉以下内容：
    - 网站导航和菜单
    - 广告和推广内容
    - 页脚信息和版权声明
    - 评论区和社交分享按钮
    - 相关文章推荐
    5. 保持内容的逻辑结构和段落层次
"""

def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False

# 文本裁剪与规范化
def _clip(text: Optional[str], max_len: int) -> str:
    if not text:
        return ""
    # 规范空白，避免无意义 token
    t = " ".join(str(text).split())
    if len(t) > max_len:
        return t[:max_len]
    return t

async def extract_contents(urls: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for url in urls:
        res = await resilient_extract(
            url=url,
            schema=ArticleContent.model_json_schema(),
            instruction=INSTRUCTION,
            provider="openai/" + ZAI_PROVIDER,
            api_token=ZAI_API_TOKEN,
            base_url=ZAI_MODEL_URL,
            selectors=None,     # 使用内置选择器集合进行渐进式稳定等待
            headless=True,      # 生产建议 True；排障可改 False
            mobile_ua=True,
            primary_selector=None
        )
        content = res.extracted or ""
        if content and _is_valid_json(content):
            parsed = json.loads(content)
            results.extend(parsed if isinstance(parsed, list) else [parsed])

    valid_results = []
    for result in results:
        if result is None:
            continue
        if result.get('error', False):
            continue
        if not result.get('main_content', '').strip():
            continue
        valid_results.append(result)
    return valid_results

# ===================== Provider 注册表 =====================
def _build_provider(name: str) -> BaseSearchProvider:
    name = name.lower().strip()
    if name in ("zhipu", "zhipuai", "zai"):
        return ZhipuSearchProvider()
    if name in ("metaso",):
        return MetasoSearchProvider()
    raise ValueError(f"Unknown provider: {name}")

def _iter_providers(providers: Optional[Iterable[str]]=None) -> List[BaseSearchProvider]:
    # 默认优先使用 zhipu；可按需要调整优先级
    default = ["zhipu"]
    names = list(providers) if providers else default
    return [_build_provider(n) for n in names]

def web_search(
    query: str,
    category: Optional[str] = None,
    extract: bool = False
) -> dict[str, str | list[dict[str, Any]] | dict[str, list[str] | int | str | bool] | None]:
    start = time.time()
    providers = ["zhipu"]
    provs = _iter_providers(providers)
    all_hits: List[SearchHit] = []

    for p in provs:
        try:
            hits = p.search(
                query,
                count=2,
                category=category,
                content_size="medium",
                intent=True
            )
            all_hits.extend(hits)
        except Exception as e:
            print(f"[web_search] provider={p.name} error: {e}")

    # 简单去重：优先依据 url，其次用 (provider, snippet) 粗粒度去重
    seen_urls = set()
    seen_snippets = set()
    deduped: List[SearchHit] = []
    for h in all_hits:
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

    print(f"search query: {query}")
    print(f"search category: {category}")
    print(f"providers used: {[p.name for p in provs]}")

    # if deduped:
    #     print(f"hits: {len(deduped)}; urls: {[h.url for h in deduped if h.url]}")

    # 紧凑化：仅保留必要字段，并限制 TOP_K_HITS
    compact_hits: List[Dict[str, str]] = []
    for h in deduped[:TOP_K_HITS]:
        if not h.url:
            continue
        compact_hits.append({
            "title": _clip(getattr(h, "title", None), MAX_TITLE_CHARS),
            "url": h.url,
            "snippet": _clip(getattr(h, "snippet", None), MAX_SNIPPET_CHARS),
        })
    # 默认不抽取正文，进一步避免 token 膨胀
    contents: List[Dict[str, Any]] = []
    if extract:
        urls = [h["url"] for h in compact_hits if h.get("url")]
        if urls:
            try:
                contents = asyncio.run(extract_contents(urls))
            except Exception as e:
                # 抽取失败不影响 hits 返回；把错误放在 stats 或 error 中
                print(f"[web_search] extract error: {e}")

    # 极简 payload：仅面向模型推理的必要字段
    payload: Dict[str, Any] = {
        "query": query,
        "category": category,
        "hits": compact_hits
    }
    # 如需保留结构化抽取（可选，默认不启用）
    if extract and contents:
        payload["contents"] = contents

    return payload

_SEEN_URLS: Set[str] = set()
_SEEN_QUERIES: Set[str] = set()

def _normalize_query(q: str) -> str:
    return " ".join((q or "").lower().split())

def reset_search_state() -> None:
    """
    在每次研究任务开始前调用，清空已见查询与URL集合，避免跨任务污染。
    """
    _SEEN_URLS.clear()
    _SEEN_QUERIES.clear()

def web_search_with_guard(
    query: str,
    category: Optional[str] = None,
    extract: bool = False
) -> Dict[str, Any]:
    """
    包装 web_search：
    - duplicate_query: 是否重复/高度相似查询（基于规范化后的字符串）
    - new_urls: 本次返回中“首次出现”的 URL 数量（基于会话内状态）
    - 其它字段与 web_search 保持一致（hits/contents）
    """
    norm_q = _normalize_query(query)
    duplicate_query = norm_q in _SEEN_QUERIES
    _SEEN_QUERIES.add(norm_q)

    base = web_search(query=query, category=category, extract=extract) or {}
    hits = base.get("hits") or []
    new_urls = 0
    for h in hits:
        url = (h.get("url") or "").strip()
        if not url:
            continue
        if url not in _SEEN_URLS:
            _SEEN_URLS.add(url)
            new_urls += 1

    # 回传原始字段，并追加增量信号
    guarded = base.copy()
    guarded["duplicate_query"] = duplicate_query
    guarded["new_urls"] = new_urls
    return guarded

def build_web_search_tool() -> Any:
    """
    工具接口保持兼容：query 必填、category 可选。
    兼容性扩展：可选 count、providers（数组）参数；extract 默认为 True，与旧行为一致。
    """
    return tool(
        name="webSearch",
        description="Search the web for information on a topic",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to achieve the todo",
                    "maxLength": 150
                },
                "category": {
                    "type": "string",
                    "enum": ["news", "company", "research paper", "github", "financial report"],
                    "description": "The category of the search if relevant"
                }
            },
            "required": ["query"]
        },
        execute=lambda query, category=None: web_search_with_guard(
            query=query,
            category=category,
            extract=False  # 默认不抽正文，保持轻量；如需正文可改 True
        )
    )
