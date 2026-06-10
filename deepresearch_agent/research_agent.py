import time
import asyncio
from typing import Dict, Any
from ai_sdk import openai, generate_text
from ai_sdk.generate_text import GenerateTextResult

from .config import QWEN_PROVIDER, QWEN_API_TOKEN, QWEN_MODEL_URL, TEMPERATURE
from .prompts import build_prompts
from .search import build_web_search_tool, reset_search_state, ResearchSession

def _compose_research_prompt(base_system: str, budget: int) -> str:
    """
    在不修改 prompts.py 的前提下，为研究代理追加“停机/限次”硬规则。
    说明：
    - 不替换原有 build_prompts，只做追加，避免丢失通用约束。
    - 与 search 的 duplicate_query/new_urls 信号配合，帮助模型在没有增量时停止继续搜索。
    """

    research_rules = f"""
硬性规则（严格遵守）：
- 工具调用总上限：{budget} 次。
- 仅在确有必要时才调用工具。若已有足够信息，立刻停止调用工具并直接给出最终答案。
- “最后一步”禁止调用任何工具，必须直接输出最终答案（纯文本）。
- 若最近 2 次搜索没有新增来源（new_urls == 0），或出现重复/高度相似查询（duplicate_query == true），请停止搜索并直接总结。
- 每个子问题最多 1 次搜索，除非明确缺少关键事实。
- 不要为“完善完美度”而反复搜索；聚焦决策所需的关键信息。

输出要求：
- 先给出“简要结论”，再给出“关键依据与来源列表”（去重域名），来源控制在 3–5 条最具代表性的条目。
- 当你准备输出最终答案时，直接用纯文本输出，不要再调用任何工具。
""".strip()

    return f"{base_system}\n\n{research_rules}"

def execute_research_agent(
    topic: str, 
    plan_dict: Dict[str, Any], 
    budget: int,
    session: ResearchSession | None = None,
) -> GenerateTextResult:
    """
    执行研究代理，进行AI驱动的研究任务。

    若传入 ResearchSession，搜索去重状态隔离在 session 内；
    否则回退到模块级全局变量（向后兼容）。
    """
    # 0) 每次任务开始前，清空搜索工具的会话状态
    if session is None:
        reset_search_state()

    # 1) 构造系统提示（先用原有的通用提示，再追加研究专用规则）
    base_system  = build_prompts(
        today=time.strftime("%Y-%m-%d"),
        total_todos=budget,
        plan=plan_dict.get("plan", [])
    )
    system = _compose_research_prompt(base_system, budget)

    # 2) 注册 WebSearch 工具（传入 session 以隔离搜索状态）
    add_tool = build_web_search_tool(session=session)

    # 执行研究代理
    result = generate_text(
        model=openai(
            model=QWEN_PROVIDER,
            api_key=QWEN_API_TOKEN,
            base_url=QWEN_MODEL_URL,
            temperature=TEMPERATURE,
        ),
        system=system,
        prompt=topic,
        temperature=TEMPERATURE,
        tools=[add_tool],
        max_steps=budget,
    )

    return result


async def execute_research_async(
    topic: str,
    plan_dict: Dict[str, Any],
    budget: int,
) -> GenerateTextResult:
    """Async wrapper for FastAPI / asyncio environments.

    Creates a fresh ResearchSession, delegates to execute_research_agent
    via asyncio.to_thread, and ensures search state is properly scoped.
    """
    session = ResearchSession()
    return await asyncio.to_thread(
        execute_research_agent,
        topic=topic,
        plan_dict=plan_dict,
        budget=budget,
        session=session,
    )
