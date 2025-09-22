import time
import json
import asyncio
from typing import Optional, Annotated
from pydantic import BaseModel, Field

from ai_sdk import generate_object, openai, generate_text, tool
from ai_sdk.generate_object import GenerateObjectResult
from ai_sdk.types import OnStepFinishResult
from deepsearch_agent.resilient_crawl import resilient_extract

MODEL = "moonshotai/kimi-k2:free"
API_KEY = "<API_KEY>"
BASE_URL = "https://openrouter.ai/api/v1"

topic = "HR高端技能在科技行业董事长中的关键作用是什么？"

class ResearchTopic(BaseModel):
    title: Annotated[
        str, 
        Field(
            min_length=10,
            max_length=70,
            description="A title for the research topic"
        )
    ]
    todos: Annotated[
        list[str], 
        Field(
            min_length=3, 
            max_length=5,
            description="A list of what to research for the given title"
        )
    ]

class ResearchPlan(BaseModel):
    plan: Annotated[
        list[ResearchTopic], 
        Field(min_length=1, max_length=10)
    ]

def generate_plan_with_retry(base_model, topic: str, max_retries: int = 3) -> Optional[GenerateObjectResult]:
    for attempt in range(max_retries):
        try:
            result = generate_object(
                model=base_model,
                schema=ResearchPlan,
                prompt=f'''
                    Plan out the research for the following topic: ${topic}.

                    CRITICAL: Generate a JSON response with this EXACT structure:
                    {{
                        "plan": [
                            {{
                                "title": "Research topic title here",
                                "todos": ["todo 1", "todo 2", "todo 3"]
                            }}
                        ]
                    }}

                    IMPORTANT FIELD NAMES:
                    - Use "title" (NOT "topic") for the research topic title
                    - Use "todos" for the list of tasks

                    CRITICAL CONSTRAINTS:
                    - You MUST generate EXACTLY 3-5 research topics, NO MORE THAN 5!
                    - Each topic MUST have 3-5 todos
                    - Strictly follow the JSON schema requirements

                    Plan Guidelines:
                    - Break down the topic into key aspects to research
                    - Generate specific, diverse search queries for each aspect
                    - Search for relevant information using the web search tool
                    - Analyze the results and identify important facts and insights
                    - The plan is limited to 15 actions, do not exceed this limit!
                    - Follow up with more specific queries as you learn more
                    - Add todos for code execution if it is asked for by the user
                    - No need to synthesize your findings into a comprehensive response, just return the results
                    - The plan should be concise and to the point, no more than 10 items
                    - Keep the titles concise and to the point, no more than 70 characters
                    - Mention any need for visualizations in the plan
                    - Make the plan technical and specific to the topic

                    REMEMBER: Maximum 5 research topics total!
                '''
            )
            return result
        except ValueError as e:
            if "does not conform to the expected schema" in str(e):
                print(f"尝试 {attempt + 1}/{max_retries} 失败，重新生成...")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                continue
            else:
                raise e

    print(f"经过 {max_retries} 次尝试仍然失败")
    return None

model = openai(model=MODEL, api_key=API_KEY, base_url=BASE_URL, temperature=0.4)
plan: GenerateObjectResult = generate_plan_with_retry(model, topic)
plan_dict = plan.object.model_dump()
print(f"plan: {plan_dict}")

total_todos = sum(len(item.get("todos", [])) for item in plan_dict.get("plan", []))
budget = max(1, total_todos)
print(f"total_todos number: {budget}")

SYSTEM_INSTRUCTIONS = """
You are an autonomous deep research analyst. Your goal is to research the given research plan thoroughly with the given tools.

Today is {today}.

PRIMARY FOCUS: SEARCH-DRIVEN RESEARCH (95% of your work)
- Prioritize SEARCH over code (no code execution available).
- Do not run all the queries at once; run them one by one and wait for results.
- Make 3-5 targeted searches per research topic to get different angles.
- Queries should be specific and focused (5-15 words).
- Vary approaches: overview → specifics → recent developments → expert opinions.
- Use categories strategically: news, research paper, company, financial report, github.
- Follow up initial searches with targeted queries based on what you learn.
- Cross-reference by searching from different angles and look for contradictions.
- Include metrics, dates, technical terms, and proper nouns in queries.
- Focus on recent developments and trends.
- Verify information with multiple searches from different sources.

SEARCH STRATEGY EXAMPLES:
- Topic: "AI model performance" → "GPT-4 benchmark results 2024", "LLM performance comparison studies", "AI model evaluation metrics research"
- Topic: "Company financials" → "Tesla Q3 2024 earnings report", "Tesla revenue growth analysis", "electric vehicle market share 2024"
- Topic: "Technical implementation" → "React Server Components best practices", "Next.js performance optimization techniques", "modern web development patterns"

RESEARCH WORKFLOW:
1) Start with broad searches to understand the landscape
2) Drill down with specific searches
3) Look for recent developments/news/research
4) Cross-validate across categories
5) Continue searching to fill any gaps in understanding

For research:
- Carefully follow the plan, do not skip any steps
- Do not use the same query twice to avoid duplicates
- Plan is limited to {totalTodos} actions with 2 extra actions in case of errors, do not exceed this limit but use to the fullest to get the most information!

Research Plan:
{plan}
"""

SYSTEM = SYSTEM_INSTRUCTIONS.format(today=time.strftime("%Y-%m-%d"), totalTodos=budget, plan=plan_dict.get("plan", []))

from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="<API_KEY>")

class ArticleContent(BaseModel):
    title: str = Field(..., description="文章标题")
    url: str = Field(..., description="文章URL")
    icon: str = Field(default="", description="文章图标URL")
    main_content: str = Field(..., description="正文主要内容")
    publish_date: str = Field(default="", description="发布日期")

def web_search(query: str, category: str = None) -> str:
    response = client.web_search.web_search(
        search_engine="search_pro_sogou",
        search_query=query,
        search_intent=True,
        count=5,  # 返回结果的条数，范围1-50，默认10
        search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
        content_size="medium"  # 控制网页摘要的字数，默认medium
    )
    urls = []
    if hasattr(response, 'search_result') and isinstance(response.search_result, list):
        urls = [result.link for result in response.search_result]
        print(f"search urls: {urls}")
    else:
        print("No search results found in response")

    provider = "openai/gpt-oss-20b:free"
    api_token = "<API_KEY>"
    model_url = "https://openrouter.ai/api/v1"
    instruction = """请从网页内容中提取核心信息，具体要求：
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

    def is_valid_json(json_str):
        """判断一个字符串是否是有效的 JSON"""
        try:
            json.loads(json_str)  # 尝试解析
            return True
        except json.JSONDecodeError:
            return False

    async def crawl_urls():
        results = []
        for url in urls:
            res = await resilient_extract(
                url=url,
                schema=ArticleContent.model_json_schema(),
                instruction=instruction,
                provider=provider,
                api_token=api_token,
                base_url=model_url,
                selectors=None,     # 使用内置选择器集合进行渐进式稳定等待
                headless=True,      # 生产建议 True；排障可改 False
                mobile_ua=True
            )
            content = res.extracted or ""
            if content and is_valid_json(content):
                parsed_content = json.loads(content)
                results.extend(parsed_content if isinstance(parsed_content, list) else [parsed_content])
        return results
    rets = asyncio.run(crawl_urls())
    return rets

add = tool(
    name="webSearch",
    description='Search the web for information on a topic',
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
    execute=web_search
)

tool_results = []
def on_step_finish(step: OnStepFinishResult):
    if step.tool_results:
        tool_results.append(step.tool_results)

res = generate_text(
    model=model,
    system=SYSTEM,
    prompt=topic,
    temperature=0.4,
    tools=[add],
    max_steps=budget,
    on_step=on_step_finish
)
print("--------------------------------------")
print(tool_results)
print("--------------------------------------")
