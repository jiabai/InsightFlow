import time
from typing import Dict, Any
from ai_sdk import openai, generate_text
from ai_sdk.generate_text import GenerateTextResult

from .config import QWEN_PROVIDER, QWEN_API_TOKEN, QWEN_MODEL_URL, TEMPERATURE
from .system_prompt import build_system_prompt
from .tools_web_search import build_web_search_tool, reset_search_state

def _compose_research_prompt(base_system: str, budget: int) -> str:
    """
    在不修改 system_prompt.py 的前提下，为研究代理追加“停机/限次”硬规则。
    说明：
    - 不替换原有 build_system_prompt，只做追加，避免丢失通用约束。
    - 与 tools_web_search 的 duplicate_query/new_urls 信号配合，帮助模型在没有增量时停止继续搜索。
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
    budget: int
) -> GenerateTextResult:
    """
    执行研究代理，进行AI驱动的研究任务
    """
    # 0) 每次任务开始前，清空搜索工具的会话状态（关键）
    reset_search_state()

    # 1) 构造系统提示（先用原有的通用提示，再追加研究专用规则）
    base_system  = build_system_prompt(
        today=time.strftime("%Y-%m-%d"),
        total_todos=budget,
        plan=plan_dict.get("plan", [])
    )
    system = _compose_research_prompt(base_system, budget)

    # 2) 注册 WebSearch 工具（内部已切换为 web_search_with_guard）
    add_tool = build_web_search_tool()

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
