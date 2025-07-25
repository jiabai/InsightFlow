import re
import random
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from be.common.database_manager import Chunk
from be.common.logger_config import setup_logging
from be.common.database_manager import DatabaseManager

def extract_json_from_llm_output(output):
    """
    从 LLM 的输出中提取 JSON 字符串并解析。
    尝试直接解析输出，如果失败则尝试从 markdown json 块中提取。

    Args:
        output (str): LLM 的原始输出字符串。

    Returns:
        dict or list or None: 解析后的 JSON 对象或列表，如果解析失败则返回 None。
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        match = re.search(r'```json\n(.*)\n```', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
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
    return f"""
    # 角色使命
    你是一位专业的文本分析专家，擅长从复杂文本中提取关键信息并生成可用于模型微调的结构化数据（仅生成问题）。
    
    ## 核心任务
    根据用户提供的文本（长度：{len(text)} 字），生成不少于 {number} 个高质量问题。
    
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

# async def _get_chunk_content(db_manager: DatabaseManager, chunk_id: str):
#     """
#     从数据库中获取指定 chunk 的内容。

#     Args:
#         db_manager: 数据库管理器实例。
#         chunk_id (str): chunk 的 ID。

#     Returns:
#         str or None: chunk 的内容，如果未找到则返回 None。
#     """
#     chunk = await db_manager.get_chunk_by_id(chunk_id)
#     if not chunk:
#         return None
#     return chunk.content

# def _generate_raw_questions(content, project_config, project_details, llm_client):
#     """
#     根据文本内容、项目配置和项目详情生成原始问题。

#     Args:
#         content (str): 文本内容。
#         project_config (dict): 项目配置。
#         project_details (dict): 项目详情。

#     Returns:
#         list or None: 生成的问题列表，如果生成失败或解析失败则返回 None。
#     """

#     number_of_questions = max(1, int(len(content) / project_config.get('questionGenerationLength', 100)))
#     question_prompt = get_question_prompt(
#         text=content,
#         number=number_of_questions,
#         language=project_config.get('language', '中文'),
#         global_prompt=project_details.get('globalPrompt', ''),
#         question_prompt=project_details.get('questionPrompt', '')
#     )
#     raw_response = llm_client.get_response(question_prompt)
#     questions = extract_json_from_llm_output(raw_response)
#     if not questions:
#         return None
#     return questions

# def _process_questions(questions, project_config):
#     """
#     处理生成的问题，例如随机移除问号。

#     Args:
#         questions (list): 原始问题列表。
#         project_config (dict): 项目配置。

#     Returns:
#         list: 处理后的问题列表。
#     """
#     return random_remove_question_mark(questions, project_config.get('questionMaskRemovingProbability', 60))

# def _label_and_save_questions(db, project_id, chunk_id, questions, tags, llm_client):
#     """
#     为问题添加标签并保存到数据库。

#     Args:
#         db_manager: 数据库管理器实例。
#         project_id (str): 项目 ID。
#         chunk_id (str): chunk 的 ID。
#         questions (list): 问题列表。
#         tags (list): 标签列表。

#     Returns:
#         list: 带有标签的问题列表。
#     """

#     tags_json = json.dumps([tag['name'] for tag in tags], ensure_ascii=False)
#     questions_json = json.dumps(questions, ensure_ascii=False)
#     label_prompt = get_add_label_prompt(tags_json, questions_json)
#     labeled_response = llm_client.get_response(label_prompt)
#     labeled_questions = extract_json_from_llm_output(labeled_response)

#     if not labeled_questions:
#         labeled_questions = [{'question': q} for q in questions]

#     db.save_questions(project_id, labeled_questions, chunk_id)
#     return labeled_questions

# async def generate_questions_for_chunk(
#     db_manager: DatabaseManager,
#     project_id: str,
#     chunk_id: str,
#     project_config: dict,
#     project_details: dict,
#     tags: list,
#     llm_config: dict
# ):
#     """
#     为指定 chunk 生成、处理、标记并保存问题。

#     Args:
#         db_manager: 数据库管理器实例。
#         project_id (str): 项目 ID。
#         chunk_id (str): chunk 的 ID。
#         project_config (dict): 项目配置。
#         project_details (dict): 项目详情。
#         tags (list): 标签列表。
#         llm_config (dict): LLM 配置。

#     Returns:
#         list or None: 带有标签的问题列表，如果处理失败则返回 None。
#     """
#     llm_client = LLMClient(llm_config)

#     content = await _get_chunk_content(db_manager, chunk_id)
#     if not content:
#         return None

#     questions = _generate_raw_questions(content, project_config, project_details, llm_client)
#     if not questions:
#         return None

#     questions = _process_questions(questions, project_config)

#     if not tags:
#         labeled_questions = [{'question': q} for q in questions]
#         db.save_questions(project_id, labeled_questions, chunk_id)
#         return labeled_questions

#     return _label_and_save_questions(db, project_id, chunk_id, questions, tags, llm_client)
