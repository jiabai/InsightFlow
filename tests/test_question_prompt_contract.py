"""Prompt contract tests for server-side question generation."""

from server.llm_knowledge_processing.utils import get_add_label_prompt, get_question_prompt


GEA_ARTICLE_SUMMARY = """
特赞科技推出企业级智能体 GEA，文章讨论企业 AI 应用如何从简单工具走向面向具体业务问题的系统能力。
文中强调 Context 和 Orchestration 对企业级 AI 落地的重要性，也提到 Pod 组织模式如何支持 AI 转型。
"""


def test_question_prompt_targets_transferable_discussion_questions():
    prompt = get_question_prompt(
        text=GEA_ARTICLE_SUMMARY,
        number=3,
        language="中文",
    )

    assert "议题问句" in prompt
    assert "可迁移" in prompt
    assert "避免阅读理解式问题" in prompt
    assert "行业、方法、组织、决策、技术落地" in prompt
    assert "默认不要把公司名、人物名、产品名作为问题主语" in prompt


def test_question_prompt_contains_gea_regression_examples():
    prompt = get_question_prompt(
        text=GEA_ARTICLE_SUMMARY,
        number=3,
        language="中文",
    )

    assert "特赞科技推出的 GEA 与传统工具有何区别" in prompt
    assert "企业级 Agent 和通用 AI 工具的价值分水岭是什么" in prompt


def test_question_prompt_preserves_existing_parameters_and_json_contract():
    prompt = get_question_prompt(
        text="一篇关于企业 AI 转型的文章。",
        number=2,
        language="English",
        global_prompt="Use concise wording.",
        question_prompt="Focus on organizational design.",
    )

    assert "English" in prompt
    assert "Use concise wording." in prompt
    assert "Focus on organizational design." in prompt
    assert '["问题1", "问题2", "..."]' in prompt


def test_question_prompt_requires_human_readable_question_wording():
    prompt = get_question_prompt(
        text="一篇关于企业 AI 转型、组织协作和业务落地的文章。",
        number=2,
        language="中文",
    )

    assert "人类读者" in prompt
    assert "自然、清晰、顺口" in prompt
    assert "避免机器翻译腔" in prompt
    assert "每个问题只聚焦一个核心思考点" in prompt
    assert "少用嵌套从句" in prompt


def test_add_label_prompt_avoids_internal_fallback_labels():
    prompt = get_add_label_prompt(
        tags_json='["组织协作", "技术落地"]',
        questions_json='["企业 AI 落地时组织能力为什么重要？"]',
    )

    assert "不要输出 uncategorized" in prompt
    assert "无法匹配时使用空字符串" in prompt
