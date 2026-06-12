import re
import random
import json

def extract_json_from_llm_output(output):
    """
    从 LLM 的输出中提取 JSON 字符串并解析。
    尝试直接解析输出，如果失败则尝试从 markdown json 块中提取。

    Args:
        output (str): LLM 的原始输出字符串。

    Returns:
        dict or list or None: 解析后的 JSON 对象或列表，如果解析失败则返回 None。
    """
    if not output or not isinstance(output, str):
        return None
    try:
        return json.loads(output)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None

def get_question_prompt(
    text,
    number,
    language='中文',
    global_prompt='',
    question_prompt=''
):
    """
    生成用于向 LLM 请求问题的提示。

    Args:
        text (str): 用于生成问题的文本内容。
        number (int): 需要生成的问题数量。
        language (str): 生成问题的语言，默认为 '中文'。
        global_prompt (str): 全局提示，添加到角色使命之前。
        question_prompt (str): 问题提示，添加到核心任务之后。

    Returns:
        str: 格式化的提示字符串。
    """
    global_prompt_section = ""
    if global_prompt:
        global_prompt_section = f"""
    ## 全局附加约束
    {global_prompt}
    """

    question_prompt_section = ""
    if question_prompt:
        question_prompt_section = f"""
    ## 本次问题生成附加要求
    {question_prompt}
    """

    return f"""
    # 角色使命
    你是一位阅读思考伙伴和议题策展者。你的任务不是把文章改写成阅读理解题，
    而是从文章案例中提炼能够启发用户继续思考的开放式议题问句。
    {global_prompt_section}
    
    ## 核心任务
    根据用户提供的文本（长度：{len(text)} 字），生成不少于 {number} 个高质量问题。
    每个问题都必须是可迁移的议题问句，输出语言必须是：{language}。
    {question_prompt_section}

    ## 生成原则
    - 优先抽象为行业、方法、组织、决策、技术落地等可迁移角度。
    - 避免阅读理解式问题，不要要求用户复述文章中的某家公司、某个人物、某个产品做了什么。
    - 默认不要把公司名、人物名、产品名作为问题主语；可以把它们作为案例来源，但问题本身要指向更通用的思考角度。
    - 问题应当开放、具体、有讨论价值，适合用户点击后继续追问或回答。
    - 不要生成事实核对题、定义题、摘要题、考试题。

    ## 面向人类读者的表达优化
    - 站在人类读者的视角写问题，问题本身要自然、清晰、顺口，读完就知道可以从哪个角度思考。
    - 每个问题只聚焦一个核心思考点，避免把多个条件、比较对象和结论塞进同一句。
    - 少用嵌套从句、抽象名词堆叠和过长限定语；必要时用短句表达因果或对比。
    - 避免机器翻译腔、模板化问法和生硬术语；专业概念要放在清楚的语境里。
    - 问题长度尽量控制在一行可读范围内，不为了显得专业而牺牲理解成本。

    ## 风格示例
    - 避免：特赞科技推出的 GEA 与传统工具有何区别？
    - 改为：企业级 Agent 和通用 AI 工具的价值分水岭是什么？
    - 避免：范凌认为 Context 和 Orchestration 分别是什么意思？
    - 改为：为什么企业 AI 落地时，上下文能力和流程编排可能比单点模型能力更关键？
    
    ## 输出格式
    - JSON 数组格式必须正确
    - 输出的 JSON 数组必须严格符合以下结构：
    ```json
    ["问题1", "问题2", "..."]
    ```

    ## 待处理文本
    {text}
    """

def get_add_label_prompt(tags_json, questions_json):
    """
    生成用于向 LLM 请求为问题添加标签的提示。

    Args:
        tags_json (str): 标签的 JSON 字符串。
        questions_json (str): 问题的 JSON 字符串。

    Returns:
        str: 格式化的提示字符串。
    """
    return f"""
    # 任务
    为以下问题列表添加标签。

    # 标签列表
    {tags_json}

    # 问题列表
    {questions_json}

    # 标签规则
    - label 必须优先使用标签列表中已经存在的标签。
    - 如果没有合适标签，label 使用空字符串 ""。
    - 不要输出 uncategorized、unlabelled、unlabeled、其他、未分类 等内部兜底标签。
    - 无法匹配时使用空字符串，不要为了凑标签而添加含糊分类。

    # 输出格式
    ```json
    [{{"question": "问题1", "label": "标签A"}}, ...]
    ```
    """

def random_remove_question_mark(questions, probability=60):
    """
    随机移除问题末尾的问号。

    Args:
        questions (list): 问题字符串列表。
        probability (int): 移除问号的概率（0-100）。

    Returns:
        list: 处理后的问题字符串列表。

    Raises:
        ValueError: 如果概率不在 0-100 范围内。
    """
    if not (0 <= probability <= 100):
        raise ValueError("Probability must be between 0 and 100")

    modified_questions = []
    for q in questions:
        if random.randint(1, 100) <= probability:
            q = q.rstrip('?？')
        modified_questions.append(q)
    return modified_questions
