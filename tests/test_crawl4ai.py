import asyncio
import random
from typing import Tuple
from pydantic import BaseModel, Field
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig
)

class ArticleContent(BaseModel):
    title: str = Field(..., description="文章标题")
    url: str = Field(..., description="文章URL")
    icon: str = Field(default="", description="文章图标URL")
    main_content: str = Field(..., description="正文主要内容")
    publish_date: str = Field(default="", description="发布日期")

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

async def main():
    # news_url = "https://www.zhihu.com/question/451245965/answer/2320601791"
    news_url = "https://www.toutiao.com/w/1826123424148492/"

    browser_config = default_browser_config(
        headless=True,
        mobile_ua=True,
        disable_images=False,
        stealth=True,
        allow_no_sandbox=False,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=news_url
        )
        if result.success:
            print("LLM 提取结果:")
            print(result.extracted_content)
            print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
