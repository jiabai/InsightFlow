#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签生成和管理模块
从 #Workspace 项目中提取的为问题列表生成标签label的代码转换为Python版本
"""

import json
import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from be.common.logger_config import setup_logging

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)


@dataclass
class Tag:
    """标签数据类"""
    id: Optional[str] = None
    label: str = ""
    project_id: str = ""
    parent_id: Optional[str] = None
    question_count: int = 0
    child: List['Tag'] = None
    
    def __post_init__(self):
        if self.child is None:
            self.child = []


@dataclass
class Question:
    """问题数据类"""
    question: str
    label: Optional[str] = None


class TagGenerator:
    """标签生成器类"""
    
    def __init__(self):
        self.project_name = ""
    
    def get_add_label_prompt(self, label_array: List[str], question_array: List[Dict]) -> str:
        """
        生成为问题添加标签的提示词
        
        Args:
            label_array: 标签数组
            question_array: 问题数组
            
        Returns:
            str: 生成的提示词
        """
        labels_text = "\n".join([f"- {label}" for label in label_array])
        questions_text = json.dumps(question_array, ensure_ascii=False, indent=2)
        
        return f"""
# Role: 标签匹配专家
- Description: 你是一名标签匹配专家，擅长根据给定的标签数组和问题数组，将问题打上最合适的领域标签。你熟悉标签的层级结构，并能根据问题的内容优先匹配二级标签，若无法匹配则匹配一级标签，最后打上"其他"标签。

### Skill:
1. 熟悉标签层级结构，能够准确识别一级和二级标签。
2. 能够根据问题的内容，智能匹配最合适的标签。
3. 能够处理复杂的标签匹配逻辑，确保每个问题都能被打上正确的标签。
4. 能够按照规定的输出格式生成结果，确保不改变原有数据结构。
5. 能够处理大规模数据，确保高效准确的标签匹配。

## Goals:
1. 将问题数组中的每个问题打上最合适的领域标签。
2. 优先匹配二级标签，若无法匹配则匹配一级标签，最后打上"其他"标签。
3. 确保输出格式符合要求，不改变原有数据结构。
4. 提供高效的标签匹配算法，确保处理大规模数据时的性能。
5. 确保标签匹配的准确性和一致性。

## OutputFormat:
1. 输出结果必须是一个数组，每个元素包含 question、和 label 字段。
2. label 字段必须是根据标签数组匹配到的标签，若无法匹配则打上"其他"标签。
3. 不改变原有数据结构，只新增 label 字段。

## 标签数组：

{labels_text}

## 问题数组：

{questions_text}

## Workflow:
1. Take a deep breath and work on this problem step-by-step.
2. 首先，读取标签数组和问题数组。
3. 然后，遍历问题数组中的每个问题，根据问题的内容匹配标签数组中的标签。
4. 优先匹配二级标签，若无法匹配则匹配一级标签，最后打上"其他"标签。
5. 将匹配到的标签添加到问题对象中，确保不改变原有数据结构。
6. 最后，输出结果数组，确保格式符合要求。

## Constrains:
1. 只新增一个 label 字段，不改变其他任何格式和数据。
2. 必须按照规定格式返回结果。
3. 优先匹配二级标签，若无法匹配则匹配一级标签，最后打上"其他"标签。
4. 确保标签匹配的准确性和一致性。
5. 匹配的标签必须在标签数组中存在，如果不存在，就打上 其他 
7. 输出结果必须是一个数组，每个元素包含 question、label 字段（只输出这个，不要输出任何其他无关内容）

## Output Example:
   ```json
   [
     {{
       "question": "XSS为什么会在2003年后引起人们更多关注并被OWASP列为威胁榜首？",
       "label": "2.2 XSS攻击"
     }}
   ]
   ```
"""
    
    def distill_tags_prompt(self, tag_path: str, parent_tag: str, 
                           existing_tags: List[str] = None, count: int = 10, 
                           global_prompt: str = "") -> str:
        """
        根据标签构造子标签的提示词
        
        Args:
            tag_path: 标签链路，例如 "知识库->体育"
            parent_tag: 主题标签名称，例如"体育"
            existing_tags: 该标签下已经创建的子标签（避免重复），例如 ["足球", "乒乓球"]
            count: 希望生成子标签的数量，例如：10
            global_prompt: 项目全局提示词
            
        Returns:
            str: 生成的提示词
        """
        if existing_tags is None:
            existing_tags = []
            
        existing_tags_text = (
            f"已有的子标签包括：{'、'.join(existing_tags)}，请不要生成与这些重复的标签。" 
            if existing_tags else ""
        )
        
        global_prompt_text = f"你必须遵循这个要求：{global_prompt}" if global_prompt else ""
        
        return f"""
你是一个专业的知识标签生成助手。我需要你帮我为主题"{parent_tag}"生成{count}个子标签。

标签完整链路是：{tag_path or parent_tag}

请遵循以下规则：
{global_prompt_text}
1. 生成的标签应该是"{parent_tag}"领域内的专业子类别或子主题
2. 每个标签应该简洁、明确，通常为2-6个字
3. 标签之间应该有明显的区分，覆盖不同的方面
4. 标签应该是名词或名词短语，不要使用动词或形容词
5. 标签应该具有实用性，能够作为问题生成的基础
6. 标签应该有明显的序号，主题为 1 汽车，子标签应该为 1.1 汽车品牌，1.2 汽车型号，1.3 汽车价格等
7. 若主题没有序号，如汽车，说明当前在生成顶级标签，子标签应为 1 汽车品牌 2 汽车型号 3 汽车价格等

{existing_tags_text}

请直接以JSON数组格式返回标签，不要有任何额外的解释或说明，格式如下：
["序号 标签1", "序号 标签2", "序号 标签3", ...]
"""
    
    def remove_leading_number(self, label: str) -> str:
        """
        移除标签开头的序号
        
        Args:
            label: 带序号的标签，例如 "1.1 汽车品牌"
            
        Returns:
            str: 移除序号后的标签，例如 "汽车品牌"
        """
        # 正则说明：
        # ^\d+       匹配开头的一个或多个数字
        # (?:\.\d+)* 匹配零个或多个「点+数字」的组合（非捕获组）
        # \s+        匹配序号后的一个或多个空格（确保序号与内容有空格分隔）
        number_prefix_regex = r'^\d+(?:\.\d+)*\s+'
        # 仅当匹配到数字开头的序号时才替换，否则返回原标签
        return re.sub(number_prefix_regex, '', label)
    
    def parse_tags_from_response(self, response: str) -> List[str]:
        """
        从LLM响应中解析标签
        
        Args:
            response: LLM的响应文本
            
        Returns:
            List[str]: 解析出的标签列表
        """
        tags = []
        
        try:
            # 尝试直接解析JSON
            tags = json.loads(response)
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试使用正则表达式提取标签
            matches = re.findall(r'"([^"]+)"', response)
            if matches:
                tags = matches
        
        return tags
    
    def match_question_to_label(self, question: str, labels: List[str]) -> str:
        """
        将问题匹配到最合适的标签
        
        Args:
            question: 问题文本
            labels: 可用标签列表
            
        Returns:
            str: 匹配的标签，如果无法匹配则返回"其他"
        """
        # 简单的关键词匹配逻辑
        question_lower = question.lower()
        
        # 优先匹配二级标签（包含点号的标签）
        secondary_labels = [label for label in labels if '.' in label]
        for label in secondary_labels:
            label_keywords = self.remove_leading_number(label).lower()
            if any(keyword in question_lower for keyword in label_keywords.split()):
                return label
        
        # 如果没有匹配到二级标签，尝试匹配一级标签
        primary_labels = [label for label in labels if '.' not in label]
        for label in primary_labels:
            label_keywords = self.remove_leading_number(label).lower()
            if any(keyword in question_lower for keyword in label_keywords.split()):
                return label
        
        # 如果都没有匹配到，返回"其他"
        return "其他"
    
    def add_labels_to_questions(self, questions: List[Dict], labels: List[str]) -> List[Dict]:
        """
        为问题列表添加标签
        
        Args:
            questions: 问题列表
            labels: 标签列表
            
        Returns:
            List[Dict]: 添加了标签的问题列表
        """
        result = []
        
        for question_data in questions:
            question_text = question_data.get('question', '')
            matched_label = self.match_question_to_label(question_text, labels)
            
            # 创建新的问题对象，包含原有数据和新的标签
            new_question = question_data.copy()
            new_question['label'] = matched_label
            result.append(new_question)
        
        return result


class TagManager:
    """标签管理器类"""
    
    def __init__(self):
        self.tags_storage = {}  # 模拟数据库存储
    
    def get_all_labels(self, tag_id: str) -> List[str]:
        """
        获取某个分类及其所有子分类的 label
        
        Args:
            tag_id: 标签ID
            
        Returns:
            List[str]: 所有相关标签的label列表
        """
        labels = []
        queue = [tag_id]
        
        while queue:
            current_id = queue.pop(0)
            tag = self.tags_storage.get(current_id)
            
            if tag:
                labels.append(tag.label)
                # 获取子分类的 ID，加入队列
                children = [child_tag for child_tag in self.tags_storage.values() 
                          if child_tag.parent_id == current_id]
                queue.extend([child.id for child in children])
        
        return labels
    
    def create_tag(self, project_id: str, label: str, parent_id: Optional[str] = None) -> Tag:
        """
        创建标签
        
        Args:
            project_id: 项目ID
            label: 标签名称
            parent_id: 父标签ID
            
        Returns:
            Tag: 创建的标签对象
        """
        tag_id = f"tag_{len(self.tags_storage) + 1}"
        tag = Tag(
            id=tag_id,
            label=label,
            project_id=project_id,
            parent_id=parent_id
        )
        self.tags_storage[tag_id] = tag
        return tag
    
    def update_tag(self, tag_id: str, label: str) -> Optional[Tag]:
        """
        更新标签
        
        Args:
            tag_id: 标签ID
            label: 新的标签名称
            
        Returns:
            Optional[Tag]: 更新后的标签对象
        """
        tag = self.tags_storage.get(tag_id)
        if tag:
            tag.label = label
            return tag
        return None
    
    def delete_tag(self, tag_id: str) -> bool:
        """
        删除标签及其所有子标签
        
        Args:
            tag_id: 要删除的标签ID
            
        Returns:
            bool: 删除是否成功
        """
        tag = self.tags_storage.get(tag_id)
        if not tag:
            return False
        
        # 获取所有子标签
        all_child_tags = self.get_all_child_tags(tag_id, tag.project_id)
        
        # 从叶子节点开始删除
        for child_tag in reversed(all_child_tags):
            if child_tag.id in self.tags_storage:
                del self.tags_storage[child_tag.id]
        
        # 删除当前标签
        if tag_id in self.tags_storage:
            del self.tags_storage[tag_id]
            return True
        
        return False
    
    def get_all_child_tags(self, parent_id: str, project_id: str) -> List[Tag]:
        """
        获取标签的所有子标签（所有层级）
        
        Args:
            parent_id: 父标签ID
            project_id: 项目ID
            
        Returns:
            List[Tag]: 所有子标签列表
        """
        result = []
        
        def fetch_child_tags(pid: str):
            # 查询直接子标签
            children = [tag for tag in self.tags_storage.values() 
                       if tag.parent_id == pid and tag.project_id == project_id]
            
            if children:
                result.extend(children)
                # 递归获取每个子标签的子标签
                for child in children:
                    fetch_child_tags(child.id)
        
        fetch_child_tags(parent_id)
        return result
    
    def batch_save_tags(self, project_id: str, tags: List[Dict]) -> None:
        """
        批量保存标签树
        
        Args:
            project_id: 项目ID
            tags: 标签树数据
        """
        # 删除项目的所有现有标签
        tags_to_delete = [tag_id for tag_id, tag in self.tags_storage.items() 
                         if tag.project_id == project_id]
        for tag_id in tags_to_delete:
            del self.tags_storage[tag_id]
        
        # 插入新的标签树
        self._insert_tags(project_id, tags)
    
    def _insert_tags(self, project_id: str, tags: List[Dict], parent_id: Optional[str] = None) -> None:
        """
        递归插入标签
        
        Args:
            project_id: 项目ID
            tags: 标签数据列表
            parent_id: 父标签ID
        """
        for tag_data in tags:
            # 插入当前节点
            created_tag = self.create_tag(
                project_id=project_id,
                label=tag_data['label'],
                parent_id=parent_id
            )
            
            # 如果有子节点，递归插入
            if 'child' in tag_data and tag_data['child']:
                self._insert_tags(project_id, tag_data['child'], created_tag.id)


class AutoDistillService:
    """自动蒸馏服务类"""
    
    def __init__(self):
        self.project_name = ""
        self.tag_generator = TagGenerator()
        self.tag_manager = TagManager()
    
    def build_tag_tree(self, config: Dict) -> None:
        """
        构建标签树
        
        Args:
            config: 配置信息，包含项目ID、主题、层级、每层标签数量等
        """
        project_id = config.get('project_id')
        topic = config.get('topic')
        levels = config.get('levels', 2)
        tags_per_level = config.get('tags_per_level', 5)
        
        # 使用已经获取的项目名称，如果未获取到，则使用主题
        project_name = self.project_name or topic
        
        def build_tags_for_level(parent_tag=None, parent_tag_path='', level=1):
            """递归构建标签树"""
            # 如果已经达到目标层级，停止递归
            if level > levels:
                return
            
            # 获取当前级别的标签
            current_level_tags = []
            
            # 模拟获取现有标签的逻辑
            if parent_tag:
                current_level_tags = [tag for tag in self.tag_manager.tags_storage.values() 
                                    if tag.parent_id == parent_tag.id]
            else:
                current_level_tags = [tag for tag in self.tag_manager.tags_storage.values() 
                                    if tag.parent_id is None and tag.project_id == project_id]
            
            # 计算需要创建的标签数量
            target_count = tags_per_level
            current_count = len(current_level_tags)
            need_to_create = max(0, target_count - current_count)
            
            # 如果需要创建标签
            if need_to_create > 0:
                parent_tag_name = topic if level == 1 else (parent_tag.label if parent_tag else '')
                
                # 构建标签路径
                if level == 1:
                    tag_path_with_project_name = project_name
                else:
                    if not parent_tag_path:
                        tag_path_with_project_name = project_name
                    elif not parent_tag_path.startswith(project_name):
                        tag_path_with_project_name = f"{project_name} > {parent_tag_path}"
                    else:
                        tag_path_with_project_name = parent_tag_path
                
                # 生成标签（这里简化为直接创建示例标签）
                for i in range(need_to_create):
                    if level == 1:
                        label = f"{i+1} {parent_tag_name}子类{i+1}"
                    else:
                        label = f"{parent_tag.label.split()[0]}.{i+1} 子标签{i+1}"
                    
                    new_tag = self.tag_manager.create_tag(
                        project_id=project_id,
                        label=label,
                        parent_id=parent_tag.id if parent_tag else None
                    )
                    current_level_tags.append(new_tag)
            
            # 如果不是最后一层，继续递归构建下一层标签
            if level < levels:
                for tag in current_level_tags:
                    # 构建标签路径
                    if parent_tag_path:
                        tag_path = f"{parent_tag_path} > {tag.label}"
                    else:
                        tag_path = f"{project_name} > {tag.label}"
                    
                    # 递归构建子标签
                    build_tags_for_level(tag, tag_path, level + 1)
        
        # 从第一层开始构建标签树
        build_tags_for_level()
    
    def generate_questions_for_tags(self, config: Dict) -> None:
        """
        为标签生成问题
        
        Args:
            config: 配置信息
        """
        project_id = config.get('project_id')
        questions_per_tag = config.get('questions_per_tag', 10)
        
        # 获取所有叶子标签（没有子标签的标签）
        all_tags = list(self.tag_manager.tags_storage.values())
        leaf_tags = []
        
        for tag in all_tags:
            if tag.project_id == project_id:
                # 检查是否有子标签
                has_children = any(child.parent_id == tag.id for child in all_tags)
                if not has_children:
                    leaf_tags.append(tag)
        
        # 为每个叶子标签生成问题（这里简化为示例）
        for tag in leaf_tags:
            for i in range(questions_per_tag):
                question_text = f"关于{tag.label}的问题{i+1}？"
                # 这里可以调用LLM生成更真实的问题
                print(f"为标签 '{tag.label}' 生成问题: {question_text}")


def main():
    """主函数，演示标签生成功能"""
    # 创建标签生成器和管理器
    tag_generator = TagGenerator()
    tag_manager = TagManager()
    
    # 示例：生成标签提示词
    print("=== 标签生成提示词示例 ===")
    prompt = tag_generator.distill_tags_prompt(
        tag_path="知识库->体育",
        parent_tag="体育",
        existing_tags=["足球", "乒乓球"],
        count=5,
        global_prompt="专注于中国体育项目"
    )
    print(prompt)
    
    print("\n=== 问题标签匹配示例 ===")
    # 示例：为问题添加标签
    labels = ["1 体育", "1.1 足球", "1.2 篮球", "1.3 乒乓球", "2 科技", "2.1 人工智能"]
    questions = [
        {"question": "足球世界杯什么时候举办？"},
        {"question": "人工智能的发展前景如何？"},
        {"question": "篮球比赛有哪些规则？"}
    ]
    
    labeled_questions = tag_generator.add_labels_to_questions(questions, labels)
    for q in labeled_questions:
        print(f"问题: {q['question']}")
        print(f"标签: {q['label']}")
        print()
    
    print("=== 标签管理示例 ===")
    # 示例：标签管理
    project_id = "project_1"
    
    # 创建标签
    root_tag = tag_manager.create_tag(project_id, "体育")
    child_tag1 = tag_manager.create_tag(project_id, "足球", root_tag.id)
    child_tag2 = tag_manager.create_tag(project_id, "篮球", root_tag.id)
    
    print(f"创建根标签: {root_tag.label} (ID: {root_tag.id})")
    print(f"创建子标签: {child_tag1.label} (ID: {child_tag1.id})")
    print(f"创建子标签: {child_tag2.label} (ID: {child_tag2.id})")
    
    # 获取所有相关标签
    all_labels = tag_manager.get_all_labels(root_tag.id)
    print(f"根标签下的所有标签: {all_labels}")
    
    print("\n=== 自动蒸馏服务示例 ===")
    # 示例：自动蒸馏服务
    auto_distill = AutoDistillService()
    auto_distill.project_name = "测试项目"
    
    config = {
        'project_id': project_id,
        'topic': '人工智能',
        'levels': 2,
        'tags_per_level': 3,
        'questions_per_tag': 2
    }
    
    print("构建标签树...")
    auto_distill.build_tag_tree(config)
    
    print("\n生成的标签:")
    for tag in auto_distill.tag_manager.tags_storage.values():
        if tag.project_id == project_id:
            indent = "  " * (1 if tag.parent_id else 0)
            print(f"{indent}{tag.label} (ID: {tag.id})")
    
    print("\n为标签生成问题...")
    auto_distill.generate_questions_for_tags(config)


if __name__ == "__main__":
    main()