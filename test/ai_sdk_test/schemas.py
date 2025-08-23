from typing import Annotated
from pydantic import BaseModel, Field


class ResearchTopic(BaseModel):
    # 使用 Annotated + Field 来添加长度约束，避免在类型注解中出现调用表达式导致的类型检查报错
    title: Annotated[
        str,
        Field(min_length=10, max_length=70, description="A title for the research topic"),
    ]
    # 对列表使用 min_length/max_length 约束（适用于序列类型）
    todos: Annotated[
        list[str],
        Field(min_length=3, max_length=5, description="A list of what to research for the given title"),
    ]

class ResearchPlan(BaseModel):
    # 计划列表使用序列长度约束
    plan: Annotated[
        list[ResearchTopic],
        Field(min_length=1, max_length=10),
    ]

class ArticleContent(BaseModel):
    title: str = Field(..., description="文章标题")
    url: str = Field(..., description="文章URL")
    icon: str = Field(default="", description="文章图标URL")
    main_content: str = Field(..., description="正文主要内容")
    publish_date: str = Field(default="", description="发布日期")

class Articles(BaseModel):
    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="文章内容")
