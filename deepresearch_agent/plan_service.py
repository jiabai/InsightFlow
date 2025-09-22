import time
from typing import Optional

from ai_sdk import generate_object, openai
from ai_sdk.generate_object import GenerateObjectResult
from ai_sdk.providers.language_model import LanguageModel

from .schemas import ResearchPlan
from .config import ZAI_PROVIDER, ZAI_API_TOKEN, ZAI_MODEL_URL, TEMPERATURE

PROMPT_EN = '''
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

PROMPT_CN = '''
请为以下研究主题制定研究计划：{topic}：

重要强调：请生成一个与以下示例完全一致结构的 JSON 响应：
{{
    "plan": [
        {{
            "title": "研究要点的标题在此处",
            "todos": ["待办事项1", "待办事项2", "待办事项3"]
        }}
    ]
}}

重要字段名称：
- 使用 "title"（不是 "topic"）作为研究要点的标题
- 使用 "todos" 作为任务列表

关键限制：
- 必须生成恰好 2 到 3 个研究要点，不得超过 3 个！
- 每个研究要点必须包含 2 到 3 个待办事项（todos），待办事项需描述详细的研究内容，不能是简单的关键词
- 每个待办事项必须是具体的，不能是模糊的，必须是可执行的
- 每个待办事项必须是独立的，不能与其他待办事项重复

- 严格遵守 JSON 模式要求

计划制定指南：
- 研究前，先将研究主题拆分为需要研究的关键要点
- 为每个要点生成具体且多样化的待搜索查询的事项
- 本研究计划将使用网络搜索工具检索相关信息
- 分析结果并识别重要的事实和见解
- 本研究计划总共不得超过 10 个待办事项
- 根据获取的新信息，进行更具体的后续查询
- 研究要点表明，无需将检索结果综合成完整的报告，只需返回结果
- 研究计划应简洁明了，研究要点总数不超过 3 项
- 研究要点标题应简洁明了，不超过 70 个字符
- 研究计划内容应具有专业性，并紧密围绕研究主题
'''

def generate_plan_with_retry(
    base_model: LanguageModel,
    topic: str,
    max_retries: int = 3
) -> Optional[GenerateObjectResult[ResearchPlan]]:
    for attempt in range(max_retries):
        try:
            result = generate_object(
                model=base_model,
                schema=ResearchPlan,
                prompt=PROMPT_CN.format(topic=topic)
            )
            return result
        except ValueError as e:
            if "does not conform to the expected schema" in str(e):
                print(f"尝试 {attempt + 1}/{max_retries} 失败，重新生成...")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            else:
                raise e

    print(f"经过 {max_retries} 次尝试仍然失败")
    return None

def generate_research_plan_and_budget(topic: str) -> tuple[dict, int] | None:
    """
    生成研究计划并计算预算
    
    Args:
        topic: 研究主题
        
    Returns:
        tuple[dict, int] | None: (计划字典, 预算数量) 或 None（如果生成失败）
    """
    # LLM 生成研究计划（带重试）
    plan_result = generate_plan_with_retry(
        base_model=openai(
            model=ZAI_PROVIDER,
            api_key=ZAI_API_TOKEN,
            base_url=ZAI_MODEL_URL,
            temperature=TEMPERATURE,
        ),
        topic=topic
    )
    if plan_result is None:
        print("Failed to generate plan after retries.")
        return None

    plan_obj = plan_result.object
    plan_dict = plan_obj.model_dump()
    print(f"plan: {plan_dict}")

    # 预算 = 所有 todos 数量（至少为 1）
    total_todos = sum(len(item.get("todos", [])) for item in plan_dict.get("plan", []))
    budget = max(1, total_todos)
    print(f"total_todos number: {budget}")

    return plan_dict, budget
