"""
A utility class for processing and splitting markdown text into manageable sections.

This module provides functionality to:
- Extract document outlines from markdown text
- Split content based on headings and length constraints 
- Generate summaries for each section
- Handle merging of short sections and splitting of long sections

The main class MarkdownSplitter offers methods to process markdown documents
while maintaining their semantic structure and ensuring sections stay within
specified length bounds.
"""

import re

class MarkdownSplitter:
    """
    MarkdownSplitter 类用于处理 Markdown 文本的解析和分割。
    它提供了提取大纲、按标题分割内容以及分割长段落等功能。
    """
    def __init__(self):
        """
        初始化 MarkdownSplitter 实例。
        """
        pass
    def split_markdown(self, text, min_length=1500, max_length=2000):
        """
        Split markdown text into sections based on length constraints and headings.

        This method processes markdown text by:
        1. Extracting the document outline
        2. Splitting content by headings
        3. Processing sections to meet length constraints
        4. Generating summaries for each section

        Args:
            text (str): The markdown text to split
            min_length (int, optional): Minimum length for each section. Defaults to 1500.
            max_length (int, optional): Maximum length for each section. Defaults to 2000.

        Returns:
            list: List of dictionaries containing processed sections with keys:
                 'summary': Generated summary for the section
                 'content': Content of the section
        """
        outline = self._extract_outline(text)

        # outline_str = '\n'.join([f"{item['level'] * '#'} {item['title']}" for item in outline])
        # print(f"Outline:\n{outline_str}")

        sections = self._split_by_headings(text, outline)

        # print(sections)
        result = self._process_sections(sections, outline, min_length, max_length)

        return [{'summary': r['summary'], 'content': r['content']} for r in result]

    def _process_sections(self, sections, outline, min_split_length, max_split_length):
        """
        Process and merge markdown sections based on length constraints.

        This method processes markdown sections by:
        1. Merging short sections that are below min_split_length
        2. Splitting long sections that exceed max_split_length
        3. Generating appropriate summaries for each resulting section

        Args:
            sections (list): List of dictionaries containing section data with keys:
                           'content', 'heading', 'level', and 'position'
            outline (list): Document outline containing heading hierarchy information
            min_split_length (int): Minimum length threshold for a section
            max_split_length (int): Maximum length threshold for a section

        Returns:
            list: List of dictionaries containing processed sections with keys:
                 'summary': Generated summary for the section
                 'content': Processed content of the section
        """
        preprocessed_sections = self._merge_short_sections(
            sections,
            min_split_length,
            max_split_length
        )

        result = []
        accumulated_section = {}

        for section in preprocessed_sections:
            content_length = len(section['content'].strip())

            # 二次处理：合并过短的段落
            if content_length < min_split_length:
                if not accumulated_section:
                    accumulated_section = dict(section)  # 初始化累积段落
                else:
                    accumulated_section['content'] += (
                        f"\n\n{'#' * section['level']} {section['heading']}\n{section['content']}"
                        if section.get('heading') else f"\n\n{section['content']}"
                    )
                    if section.get('heading'):
                        if 'headings' not in accumulated_section:
                            accumulated_section['headings'] = []
                        accumulated_section['headings'].append({
                            'heading': section['heading'],
                            'level': section['level'],
                            'position': section['position']
                        })

                accumulated_length = len(accumulated_section['content'].strip())
                if accumulated_length >= min_split_length:
                    self._process_accumulated_sections(
                        accumulated_section,
                        outline,
                        min_split_length,
                        max_split_length,
                        result
                    )
                    accumulated_section = {}
                continue
            self._process_accumulated_sections(
                accumulated_section,
                outline,
                min_split_length,
                max_split_length,
                result
            )
            accumulated_section = {}

            # 处理过长的段落
            if content_length > max_split_length:
                sub_sections = self._split_long_section(
                    section,
                    max_split_length
                )  # 分割长段落
                for i, sub_content in enumerate(sub_sections):
                    summary = self._generate_enhanced_summary(
                        section,
                        i + 1,
                        len(sub_sections)
                    )
                    result.append({
                        'summary': summary,
                        'content': sub_content
                    })
            else:
                summary = self._generate_enhanced_summary(

                    section,
                    outline
                )
                if section.get('heading'):
                    heading = '#' * section['level'] + ' ' + section['heading']
                    content = f"{heading}\n{section['content']}"
                else:
                    content = section['content']
                result.append({
                    'summary': summary,
                    'content': content
                })

        self._process_accumulated_sections(
            accumulated_section,
            outline,
            min_split_length,
            max_split_length,
            result
        )

        return result

    def _extract_outline(self, text):

        """
        从 Markdown 文本中提取标题大纲。

        Args:
            text (str): Markdown 文本内容。
            
        Returns:
            list: 包含标题信息的字典列表，每个字典包含：
                  - level (int): 标题级别 (1-6)。
                  - title (str): 标题文本。
                  - position (int): 标题在文本中的起始位置。
        """
        outline_regex = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*\{#[\w-]+\})?\s*$", re.MULTILINE)
        outline = []
        for match in outline_regex.finditer(text):
            level = len(match.group(1))
            title = match.group(2).strip()
            outline.append({"level": level, "title": title, "position": match.start()})
        return outline

    def _split_by_headings(self, text, outline):
        """
        Split markdown text into sections based on headings from the outline.

        Args:
            text (str): The markdown text content to split.
            outline (list): List of dictionaries containing heading information with keys:
                          - level (int): Heading level (1-6)
                          - title (str): Heading text
                          - position (int): Starting position of heading in text

        Returns:
            list: List of dictionaries containing section information with keys:
                 - heading (str): Section heading text (None for content before first heading)
                 - level (int): Heading level (0 for content before first heading)
                 - content (str): Content text under the heading
                 - position (int): Starting position of the section in original text
        """
        # 如果大纲为空，则整个文本作为一个部分返回
        if not outline:
            return [
                {
                    "heading": None,
                    "level": 0,
                    "content": text,
                    "position": 0,
                }
            ]

        sections = []

        # 添加第一个标题之前的内容（如果存在）
        if outline[0]["position"] > 0:
            front_matter = text[0 : outline[0]["position"]].strip()
            if len(front_matter) > 0:
                sections.append(
                    {
                        "heading": None,
                        "level": 0,
                        "content": front_matter,
                        "position": 0,
                    }
                )

        # 遍历大纲，分割每个标题下的内容
        for i, current in enumerate(outline):
            next_heading = outline[i + 1] if i + 1 < len(outline) else None

            heading_line = text[current["position"] :].split('\n', 1)[0]
            start_pos = current["position"] + len(heading_line) + 1
            end_pos = next_heading["position"] if next_heading else len(text)

            # 提取当前标题下的内容
            content = text[start_pos:end_pos].strip()

            sections.append(
                {
                    "heading": current["title"],
                    "level": current["level"],
                    "content": content,
                    "position": current["position"],
                }
            )
        return sections

    def _split_long_section(self, section, max_length):
        """
        Split a long section of text into smaller subsections based on a maximum length.

        Args:
            section (dict): A dictionary containing the section information with 
            at least a 'content' key
            max_length (int): The maximum length allowed for each subsection

        Returns:
            list: A list of strings, where each string is a subsection of the original content,
                  split at natural break points (newlines or periods) while respecting the 
                  max_length constraint
        """
        content = section['content']
        sub_sections = []
        current_pos = 0

        while current_pos < len(content):
            # 找到当前位置到max_length范围内的最后一个句号或换行符
            split_point = -1
            search_end = min(current_pos + max_length, len(content))

            # 优先在换行符处分割
            last_newline = content.rfind('\n\n', current_pos, search_end)
            if last_newline != -1:
                split_point = last_newline + 2 # 包含两个换行符
            else:
                # 其次在句号处分割
                last_period = content.rfind('.', current_pos, search_end)
                if last_period != -1:
                    split_point = last_period + 1
                else:
                    # 如果没有合适的分割点，则强制在max_length处分割
                    split_point = search_end

            # 确保分割点不会导致空段落或过小的段落，并且不会超出内容长度
            if split_point <= current_pos or split_point > len(content):
                split_point = search_end # 强制分割

            sub_sections.append(content[current_pos:split_point].strip())
            current_pos = split_point

        return sub_sections

    def _process_accumulated_sections(
        self,
        accumulated_section,
        outline,
        min_split_length,
        max_split_length,
        result
    ):
        """
        Process accumulated sections and add them to the result list.

        This helper method handles the processing of accumulated sections by:
        1. Checking if the accumulated section meets minimum length requirements
        2. Generating appropriate summaries for the section
        3. Splitting sections that exceed maximum length
        4. Adding processed sections to the result list

        Args:
            accumulated_section (dict): Dictionary containing the accumulated section data
                                      with keys like 'content', 'heading', etc.
            outline (list): Document outline containing heading hierarchy information
            min_split_length (int): Minimum length threshold for a section
            max_split_length (int): Maximum length threshold for a section
            result (list): List to store the processed sections, each containing
                          'summary' and 'content' keys

        Returns:
            None: Modifies the result list in-place
        """
        if not accumulated_section:
            return
        accumulated_length = len(accumulated_section['content'].strip())
        if accumulated_length >= min_split_length:
            summary = self._generate_enhanced_summary(accumulated_section, outline)
            if accumulated_length > max_split_length:
                sub_sections = self._split_long_section(accumulated_section, max_split_length)

                for i, sub_content in enumerate(sub_sections):
                    result.append({
                        'summary': f'{summary} - Part {i + 1}/{len(sub_sections)}',
                        'content': sub_content
                    })
            else:
                result.append({
                    'summary': summary,
                    'content': accumulated_section['content']
                })

    def _merge_short_sections(self, sections, min_split_length, max_split_length):
        """
        Merge consecutive short sections that are below the minimum length threshold.

        This method processes a list of markdown sections and attempts to merge sections
        that are shorter than min_split_length, while ensuring the merged content does
        not exceed max_split_length.

        Args:
            sections (list): List of dictionaries containing section data with keys:
                           'content', 'heading', 'level', and 'position'
            min_split_length (int): Minimum length threshold for a section
            max_split_length (int): Maximum length threshold for a section

        Returns:
            list: List of preprocessed sections where short sections have been merged
                 when possible. Each section maintains the original structure with
                 additional 'headings' key for tracking merged section headers.
        """
        preprocessed_sections = []
        current_section = {}

        for section in sections:
            content_length = len(section['content'].strip())

            if content_length < min_split_length and current_section:
                merged_content = (
                    f"{current_section['content']}\n\n"
                    f"{'#' * section['level']} {section['heading']}\n"
                    f"{section['content']}"
                ) if section.get('heading') else (
                    f"{current_section['content']}\n\n"
                    f"{section['content']}"
                )

                if len(merged_content) <= max_split_length:
                    current_section['content'] = merged_content
                    if section.get('heading'):
                        if 'headings' not in current_section:
                            current_section['headings'] = []
                        current_section['headings'].append({
                            'heading': section['heading'],
                            'level': section['level'],
                            'position': section['position']
                        })
                    continue

            if current_section:
                preprocessed_sections.append(current_section)

            current_section = dict(section)
            if section.get('heading'):
                current_section['headings'] = [
                    {
                        'heading': section['heading'],
                        'level': section['level'], 
                        'position': section['position']
                    }
                ]
            else:
                current_section['headings'] = []

        if current_section:
            preprocessed_sections.append(current_section)
        return preprocessed_sections

    def _get_doc_title_prefix(self, outline):
        """
        获取文档标题前缀，通常是第一个一级标题。

        Args:
            outline (list): 文档大纲列表。

        Returns:
            str: 文档标题前缀，如果不存在一级标题则返回“文档”。
        """
        if outline and outline[0]['level'] == 1:
            return outline[0]['title']
        return "文档"

    def _format_summary_with_part_info(self, summary, part_index, total_parts):
        """
        格式化摘要，如果存在部分信息则添加。

        Args:
            summary (str): 基础摘要字符串。
            part_index (int, optional): 当前部分的索引。
            total_parts (int, optional): 总部分数。

        Returns:
            str: 格式化后的摘要字符串。
        """
        if part_index is not None and total_parts is not None:
            return f"{summary} (Part {part_index}/{total_parts})"
        return summary

    def _build_heading_paths(self, section, outline):
        """
        为给定部分中的所有标题构建完整的标题路径。

        Args:
            section (dict): 包含 'headings' 的部分字典。
            outline (list): 完整的文档大纲。

        Returns:
            list: 包含所有标题路径字符串的列表。
        """
        paths = []
        for heading_info in section.get('headings', []):
            # 找到当前标题在outline中的索引
            current_idx = -1
            for i, item in enumerate(outline):
                if (item['title'] == heading_info['heading'] and 
                    item['level'] == heading_info['level']):
                    current_idx = i
                    break

            if current_idx == -1:
                continue

            path = [heading_info['heading']]
            current_level = heading_info['level']

            # 向上查找父标题
            for i in range(current_idx - 1, -1, -1):
                if outline[i]['level'] < current_level:
                    path.insert(0, outline[i]['title'])
                    current_level = outline[i]['level']
                if current_level == 1:
                    break
            paths.append(' > '.join(path))
        return paths

    def _build_heading_path(self, section, outline):
        """
        构建从根标题到当前标题的路径。

        Args:
            section (dict): 包含 'heading' 和 'level' 的部分字典。
            outline (list): 完整的文档大纲。

        Returns:
            list: 包含标题路径的字符串列表。
        """
        current_heading_title = section.get('heading')
        current_heading_level = section.get('level')

        if not current_heading_title or current_heading_level is None:
            return []

        path = [current_heading_title]
        current_level = current_heading_level

        # 找到当前标题在outline中的索引
        current_idx = -1
        for i, item in enumerate(outline):
            if item['title'] == current_heading_title and item['level'] == current_heading_level:
                current_idx = i
                break

        if current_idx == -1:
            return []

        # 向上查找父标题
        for i in range(current_idx - 1, -1, -1):
            if outline[i]['level'] < current_level:
                path.insert(0, outline[i]['title'])
                current_level = outline[i]['level']
            if current_level == 1:
                break
        return path

    def _find_common_prefix_summary(self, paths):
        """
        查找多个标题路径的共同前缀，并生成一个简洁的总结字符串。
        如果存在共同前缀，则将其提取出来，并将不同的部分用方括号 `[]` 括起来。
        例如：如果路径是 "A > B > C" 和 "A > B > D"，则总结为 "A > B > [C, D]"。

        Args:
            paths (list): 包含标题路径字符串的列表，例如 ["A > B > C", "A > B > D"]。

        Returns:
            str: 生成的总结字符串。
                 如果路径为空，返回空字符串。
                 如果只有一个路径，返回该路径本身。
                 如果没有共同前缀，返回所有路径用逗号连接的字符串。
        """
        if not paths:
            return ''
        if len(paths) == 1:
            return paths[0]

        first_path = paths[0]
        segments = first_path.split(' > ')

        # 遍历第一个路径的每个前缀，检查是否是所有路径的共同前缀
        for i in range(len(segments) - 1):
            prefix = ' > '.join(segments[:i+1])
            is_common_prefix = True
            for j in range(1, len(paths)):
                if not paths[j].startswith(prefix + ' > '):
                    is_common_prefix = False
                    break
            # 如果找到了共同前缀
            if is_common_prefix:
                summary = prefix + ' > ['
                # 提取每个路径中共同前缀之后的部分
                for j, path in enumerate(paths):
                    unique_part = path[len(prefix) + 3:] # +3 for ' > ['
                    summary += (', ' if j > 0 else '') + unique_part
                summary += ']'
                return summary
        # 如果没有找到共同前缀，则将所有路径用逗号连接
        return ', '.join(paths)

    def _generate_summary_for_multi_headings(
        self,
        section,
        outline,
        part_index,
        total_parts
    ):
        headings_in_section = section.get('headings', [])
        if not headings_in_section:
            return self._format_summary_with_part_info(
                self._get_doc_title_prefix(outline) + " - 多个子标题段落", part_index, total_parts
            )

        # 提取所有标题文本并用 " - " 连接
        summary_parts = [h['heading'] for h in headings_in_section]
        base_summary = " - ".join(summary_parts)
        return self._format_summary_with_part_info(
                    base_summary,
                    part_index,
                    total_parts
                )

    def _generate_summary_for_single_heading(
        self,
        section,
        outline,
        part_index,
        total_parts
    ):
        heading_path = self._build_heading_path(section, outline)
        if heading_path:
            base_summary = " - ".join(heading_path)
        else:
            base_summary = section.get('heading', '未命名段落')
        return self._format_summary_with_part_info(
                    base_summary,
                    part_index,
                    total_parts
                )

    def _generate_enhanced_summary(
        self,
        section,
        part_num=None,
        total_parts=None
    ):
        """
        Generate an enhanced summary for a markdown section.

        This method creates a summary based on section headings or content.
        If the section contains multiple headings, it combines them.
        For split sections, it adds part numbering information.

        Args:
            section (dict): Dictionary containing section data with optional keys:
                          'headings': List of heading dictionaries
                          Each heading dictionary contains:
                              'heading': Heading text
                              'level': Heading level
                              'position': Position in document
            part_num (int, optional): Current part number for split sections
            total_parts (int, optional): Total number of parts for split sections

        Returns:
            str: Generated summary string, optionally with part numbering
                 Format: "Heading1 - Heading2 (Part X/Y)" or "Content Summary"
        """
        # 如果部分包含标题，则使用这些标题作为摘要
        if section.get('headings'):
            summary_parts = [f"{h['heading']}" for h in section['headings']]
            base_summary = " - ".join(summary_parts)
        else:
            # 如果没有标题，尝试从大纲中找到最近的标题（简化逻辑）
            base_summary = "内容摘要"

        # 如果是分割后的部分，添加部分编号
        if part_num is not None and total_parts is not None:
            return f"{base_summary} (Part {part_num}/{total_parts})"
        return base_summary
