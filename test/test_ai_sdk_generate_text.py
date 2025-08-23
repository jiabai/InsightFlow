import time,json
from typing import Optional
from ai_sdk import tool, generate_text, openai
from ai_sdk.types import OnStepFinishResult

MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
API_KEY = "<API_KEY>"
BASE_URL = "https://api.siliconflow.cn/v1"

SYSTEM = '''
你是一名能独立开展研究工作，无需过多外部指令，即可完成研究任务的深度研究分析师。你的目标是利用所提供的搜索工具，对给定的研究计划进行 彻底深入的研究。

今天是 2025-08-21。

主要工作的重点：以搜索驱动的研究为主（占工作的 95%）
- 优先使用“搜索”功能，而非代码执行（无代码执行可用）
- 不要一次性运行所有查询，请逐个执行待办事项并等待结果
- 每个研究要点进行 3 到 5 次有针对性的搜索，以获取不同角度的信息。
- 查询应具体且聚焦（5 到 15 个词）。
- 采用分层次、递进式的研究或分析思路：概览 → 具体细节 → 最新动态 → 专家观点
- 战略性地运用不同信息类别：新闻、研究论文、公司、财务报告、GitHub 等。
- 根据初步搜索获得的信息，进一步开展有针对性的查询。
- 通过多角度搜索进行交叉验证，并主动查找信息中的矛盾点。
- 在查询中要包含具体要素：指标、日期、专业术语和专有名词。
- 重点关注最新发展和趋势。
- 通过从不同来源进行多次搜索来交叉核对信息，验证信息的准确性。

搜索策略示例：
- 主题：“AI 模型性能” → “GPT-4 2024 基准测试结果”、“大语言模型性能对比研究”、“AI 模型评估指标研究”
- 主题：“公司财务状况” → “特斯拉 2024 年第三季度财报”、“特斯拉收入增长分析”、“2024 年电动汽车市场份额”
- 主题：“技术实现” → “React 服务端组件最佳实践”、“Next.js 性能优化技术”、“现代 Web 开发模式”

研究工作流程：
1）先进行广泛的搜索，以了解整体情况
2）再通过具体查询深入挖掘
3）查找最新进展、新闻或研究成果
4）跨类别交叉验证信息，确保信息的准确性和一致性
5）持续搜索，填补理解上的任何空白

进行研究时：
- 严格遵循研究计划，不要跳过任何步骤
- 避免重复使用相同的查询，防止出现重复内容
- 研究计划总共限制为 15 个操作，允许额外增加 2 次操作以应对错误情况。不要超出此限制，但应充分利用这些操作以获取尽可能多的信息！      

研究计划如下：
[
    {
        'title': 'HR高端技能的定义与范畴', 
        'todos': [
            '查找HR高端技能在科技行业的标准定义', 
            '识别科技行业董事长所需的核心HR能力', 
            '分析高端HR技能与战略领导力的关系'
        ]
    }, 
    {
        'title': '董事长在科技企业中的HR角色', 
        'todos': [
            '研究科技行业董事长在人才战略中的实际职责', 
            '对比传统企业与科技企业董事长的HR参与度', 
            '分析董事长如何影响组织文化与人才发展'
        ]
    }, 
    {
        'title': '高端HR技能对创新的影响', 
        'todos': [
            '检索高端HR技 能如何促进科技企业创新', 
            '分析人才吸引与保留对研发效率的作用', 
            '研究多元化团队构建与创新绩效的关系'
        ]
    }, 
    {
        'title': '典型案例分析：成功 董事长的HR实践', 
        'todos': [
            '选取3位科技行业董事长进行HR行为分析', 
            '查找其在人才战略、组织变革中的具体举措', 
            '评估其HR决策对企业长期发展的影响'
        ]
    }, 
    {
        'title': 'HR技能与企业绩效的关联性', 
        'todos': [
            '搜索HR高端技能与企业财务绩效的相关研究', 
            '分析董事长HR能力与公司市值、 增长率的关系', 
            '识别关键绩效指标（KPI）与HR策略的匹配度'
        ]
    }
]
'''

PROMPT = '''
HR高端技能在科技行业董事长中的关键作用是什么？
'''

def web_search(query: str, category: Optional[str] = None,) -> str:

    print(f"search: {query}, category: {category}")

    payload = {
        "query": query,
        "category": category,
        "summary": "Top findings about the query.",
        "meta": {
            "timestamp": int(time.time()),
            "note": "Provide next query if any. Do not merge queries."
        }
    }
    return json.dumps(payload, ensure_ascii=False)

test_tool = tool(
    name="web_search",
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
            },
        },
        "required": ["query"],
    },
    execute=web_search
)
model = openai(model=MODEL, api_key=API_KEY, base_url=BASE_URL, temperature=0.4)

def on_step_finish(step: OnStepFinishResult):
    print(f"step_type {step.step_type}, finish_reason {step.finish_reason}")
    print(f"tool_calls: {step.tool_calls}")
    try:
        body = step.response.body
        print("[raw_response]", body)
        if isinstance(body, dict):
            # 常见位置：choices[0].message.tool_calls
            choices = body.get("choices") or []
            if choices:
                msg = choices[0].get("message", {})
                print("[message.tool_calls]", msg.get("tool_calls"))
                print("[message.content]", msg.get("content"))
                print("[finish_reason_raw]", choices[0].get("finish_reason"))
    except Exception as e:
        print("print raw_response error:", e)

result = generate_text(
    model=model,
    system=SYSTEM,
    prompt=PROMPT,
    tools=[test_tool],
    max_steps=10,
    on_step=on_step_finish
)

# if result.tool_results:
#     for item in result.tool_results:
#         print(item.result)
