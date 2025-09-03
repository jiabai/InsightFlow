from typing import cast, Iterable
import json
import time
from openai import OpenAI
from openai.types import ResponseFormatJSONObject
from openai.types.chat.completion_create_params import ResponseFormat
from openai.types.chat import ChatCompletionMessageParam

DEFAULT_MODEL = "openai/gpt-oss-20b:free"
API_KEY = "<API_KEY>"
BASE_URL = "https://openrouter.ai/api/v1"

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

TOOLS AVAILABLE:
- webSearch: Search the web for information and fetch contents.
  input: {{"query": string (max 150 chars), "category": one of ["news", "company", "research paper", "github", "financial report"] (optional) }}

ACTION FORMAT (JSON ONLY):
Return ONLY a JSON object for each step. Two possible actions:

1) Tool call:
{{
  "action": "tool",
  "tool": "webSearch",
  "input": {{"query": "...", "category": "news|company|research paper|github|financial report" (optional) }}
}}

2) Finalize:
{{
  "action": "final",
  "text": "Concise summary of key findings (no markdown needed)"
}}

CONSTRAINTS:
- No code execution is available.
- Do not exceed the step budget: {{budget}} steps (based on the research plan).
- Do not repeat the exact same query twice.
- Carefully follow the plan steps and stay on-topic.
"""

PROMPT = "HR高端技能在科技行业董事长中的关键作用是什么？"
PLAN = {
  "plan": [
    {
      "title": "Define High-End HR Skills for Tech Chairpersons",
      "todos": [
        "Search for \"high‑end HR skills definition\" and summarize key competencies",
        "Compile a taxonomy of executive HR skills from tech industry reports",
        "Identify gaps between traditional HR and high‑end HR in board roles"
      ]
    },
    {
      "title": "Assess HR Influence on Tech Board Decision‑Making",
      "todos": [
        "Query \"HR impact on board decisions tech companies\" and extract case studies",
        "Analyze how HR input shapes strategic choices in tech firms",
        "Document examples of HR‑led initiatives influencing board outcomes"
      ]
    },
    {
      "title": "Identify Key HR Competencies Driving Innovation",
      "todos": [
        "Search \"HR skills fostering innovation in tech\" and list top skills",
        "Review talent acquisition strategies used by leading tech chairpersons",
        "Evaluate the role of HR analytics in board‑level innovation decisions"
      ]
    },
    {
      "title": "Visualize HR Skill Impact Metrics",
      "todos": [
        "Collect performance data linking HR competencies to company KPIs",
        "Design a dashboard layout to display HR influence on tech outcomes",
        "Create sample charts (e.g., bar, scatter) illustrating HR impact trends"
      ]
    }
  ]
}
total_todos = sum(len(item.get("todos", [])) for item in PLAN.get("plan", []))
budget = max(1, total_todos)
today = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
SYSTEM = SYSTEM_INSTRUCTIONS.format(today=today, budget=budget)

USER = (
        f"Research prompt: {PROMPT}\n\n"
        f"Research Plan (follow strictly):\n{json.dumps(PLAN, ensure_ascii=False)}\n\n"
        "Return JSON actions only as specified."
    )

MESSAGES = [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": USER},
]

response_format_param = ResponseFormatJSONObject(type='json_object')

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

try:
    chat_completion = client.chat.completions.create(
        messages=cast(Iterable[ChatCompletionMessageParam], MESSAGES),
        model=DEFAULT_MODEL,
        temperature=0.5,
        stream=False,
        response_format=cast(ResponseFormat, cast(object, response_format_param))
    )
    print(chat_completion.choices[0].message.content)
except Exception as e:
    print(f"An error occurred: {e}")
