import re
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMExtractionStrategy,
    LLMConfig,
)

# ---------------- Data Structures ----------------

@dataclass
class ResilientResult:
    success: bool
    html: str
    text: str
    final_url: str
    status_code: int
    used_selector: Optional[str]
    attempt: int
    error: Optional[str] = None

@dataclass
class ResilientLLMResult:
    success: bool
    extracted: str
    final_url: str
    status_code: int
    used_selector: Optional[str]
    attempt: int
    error: Optional[str] = None

# ---------------- Simplified Default Selectors ----------------
# Only keep the top-3 likely containers to minimize time and anti-bot triggers
DEFAULT_SELECTORS = ["article", ".content", "main"]

# ---------------- UA/Viewport Helpers ----------------

_MOBILE_UAS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; Pixel 5 Build/SPB4.210715.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
]
_DESKTOP_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/120.0.0.0 Safari/537.36",
]

def _rand_ua(mobile_ua: bool) -> str:
    pool = _MOBILE_UAS if mobile_ua else _DESKTOP_UAS
    return random.choice(pool)

def _rand_viewport(mobile_ua: bool) -> Tuple[int, int]:
    if mobile_ua:
        base_w, base_h = 390, 844
        return base_w + random.randint(-20, 20), base_h + random.randint(-30, 30)
    else:
        base_w, base_h = 1366, 768
        return base_w + random.randint(-40, 40), base_h + random.randint(-40, 40)

# ---------------- Utilities ----------------

def _simple_html_to_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t\x0b\x0c\r]+", " ", text)
    text = re.sub(r"\n\s+\n", "\n\n", text)
    return text.strip()

def _pick_fields(result):
    success = getattr(result, "success", False)
    html = getattr(result, "html", "") or getattr(result, "raw_html", "") or getattr(result, "cleaned_html", "") or ""
    text = getattr(result, "markdown", "") or getattr(result, "markdown_v2", "") or getattr(result, "text", "") or ""
    final_url = getattr(result, "final_url", None) or getattr(result, "url", "") or ""
    status_code = getattr(result, "status_code", 0) or 0
    error = getattr(result, "error_message", None) or getattr(result, "error", None)
    return success, html, text, final_url, status_code, error

def enough(text_len: int, html_len: int, min_text: int = 600, min_html: int = 50000) -> bool:
    return text_len >= min_text or html_len >= min_html

# ---------------- Browser Config ----------------

def default_browser_config(
    headless: bool = True,
    mobile_ua: bool = True,
    disable_images: bool = False,   # keep images to mimic real users
    stealth: bool = True,           # light stealth
    allow_no_sandbox: bool = False, # usually not needed on Windows
) -> BrowserConfig:
    ua = _rand_ua(mobile_ua)
    vw, vh = _rand_viewport(mobile_ua)

    extra = []
    if headless:
        extra.append("--headless=new")
    if stealth:
        extra.append("--disable-blink-features=AutomationControlled")
    if disable_images:
        extra.append("--blink-settings=imagesEnabled=false")
    if allow_no_sandbox:
        extra.append("--no-sandbox")
        extra.append("--disable-dev-shm-usage")

    return BrowserConfig(
        headless=headless,
        browser_type="chromium",
        user_agent=ua,
        extra_args=extra,
        viewport_width=vw,
        viewport_height=vh,
    )

# ---------------- Fetch: Fast and Minimal Attempts ----------------

async def resilient_fetch(
    url: str,
    selectors: Optional[List[str]] = None,
    headless: bool = True,
    mobile_ua: bool = True,
    disable_images: bool = False,
    stealth: bool = True,
) -> ResilientResult:
    """
    Fast mode:
      1) single attempt with wait_for=None
      2) then try at most 3 selectors: ["article", ".content", "main"], each once
      No body fallback, no global retries. If fail, return failure to skip URL.
    """
    selectors = (selectors or DEFAULT_SELECTORS)[:3]

    browser_config = default_browser_config(
        headless=headless,
        mobile_ua=mobile_ua,
        disable_images=disable_images,
        stealth=stealth,
        allow_no_sandbox=False,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Attempt 1: no wait (fast probe)
        cfg1 = CrawlerRunConfig(
            word_count_threshold=1,
            wait_for=None,
            cache_mode=CacheMode.ENABLED,
            page_timeout=30000,
            wait_for_timeout=10000,
        )
        r1 = await crawler.arun(url=url, config=cfg1)
        s1, h1, t1, fu1, sc1, e1 = _pick_fields(r1)
        if not t1 and h1:
            t1 = _simple_html_to_text(h1)
        if s1 and enough(len(t1), len(h1)):
            return ResilientResult(True, h1, t1, fu1 or url, sc1, None, attempt=1)

        # Attempts 2-4: try the three likely selectors, short timeouts
        attempt = 2
        last_err = e1
        for sel in selectors:
            cfg2 = CrawlerRunConfig(
                word_count_threshold=1,
                wait_for=sel,              # treated as CSS selector in crawl4ai
                cache_mode=CacheMode.ENABLED,
                page_timeout=35000,
                wait_for_timeout=12000,
            )
            r2 = await crawler.arun(url=url, config=cfg2)
            s2, h2, t2, fu2, sc2, e2 = _pick_fields(r2)
            if not t2 and h2:
                t2 = _simple_html_to_text(h2)
            if s2 and enough(len(t2), len(h2)):
                return ResilientResult(True, h2, t2, fu2 or url, sc2, sel, attempt=attempt)
            last_err = e2 or last_err
            attempt += 1

        # Fail fast: skip URL
        return ResilientResult(False, "", "", url, 0, None, attempt=attempt - 1, error=last_err)

# ---------------- LLM Extraction: Single-Pass ----------------

async def resilient_extract(
    url: str,
    schema: dict,
    instruction: str,
    provider: str,
    api_token: str,
    base_url: str,
    selectors: Optional[List[str]] = None,
    headless: bool = True,
    mobile_ua: bool = True,
    disable_images: bool = False,
    stealth: bool = True,
    primary_selector: Optional[str] = None,  # default to first of ["article", ".content", "main"]
) -> ResilientLLMResult:
    """
    Single-pass LLM extraction:
      - Perform a single navigation with extraction strategy.
      - Use primary_selector if provided; otherwise use the first of the top-3 list.
      - If no extracted content, return failure and let the caller skip the URL.
    """
    # sel_order = (selectors or DEFAULT_SELECTORS)[:3]
    # sel = primary_selector or (sel_order[0] if sel_order else None)

    browser_config = default_browser_config(
        headless=headless,
        mobile_ua=mobile_ua,
        disable_images=disable_images,
        stealth=stealth,
        allow_no_sandbox=False
    )
    # print("*****************************")
    # print(browser_config.dump())
    # print("*****************************")

    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider=provider,
            api_token=api_token,
            base_url=base_url,
        ),
        schema=schema,
        extraction_type="schema",
        instruction=instruction,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        cfg = CrawlerRunConfig(
            word_count_threshold=1,
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
        )
        # print("------------------------------")
        # print(cfg.dump())
        # print("------------------------------")

        r = await crawler.arun(
            url=url,
            config=cfg
        )
        success, _, _, final_url, status_code, error = _pick_fields(r)
        extracted = getattr(r, "extracted_content", "") or ""

        return ResilientLLMResult(
            success=bool(success and extracted),
            extracted=extracted,
            final_url=final_url or url,
            status_code=status_code or 0,
            used_selector=None,
            attempt=1,
            error=error,
        )
