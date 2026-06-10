"""
DeepResearch Agent — AI-assisted deep research module.

A three-stage pipeline that takes a research topic and produces a
structured report with cited sources:

    1. Plan  — generate a research plan and budget
    2. Research — execute web searches via tool-calling AI
    3. Generate — extract contents and produce the final report

Usage (standalone):
    from deepresearch_agent import generate_plan, execute_research, research_async

    plan, budget = generate_plan("topic")
    result = execute_research("topic", plan, budget)

    # or async (for FastAPI / asyncio environments):
    result = await research_async("topic")
"""

from .plan import generate_research_plan_and_budget as generate_plan
from .research_agent import execute_research_agent as execute_research
from .research_agent import execute_research_async as research_async
from .search import web_search, extract_contents, build_web_search_tool, ResearchSession
from .schemas import ResearchPlan, ResearchTopic, Articles, ArticleContent

__all__ = [
    "generate_plan",
    "execute_research",
    "research_async",
    "web_search",
    "extract_contents",
    "build_web_search_tool",
    "ResearchSession",
    "ResearchPlan",
    "ResearchTopic",
    "Articles",
    "ArticleContent",
]
