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
        outline = self.extract_outline(text)
        
        # outline_str = '\n'.join([f"{item['level'] * '#'} {item['title']}" for item in outline])
        # print(f"Outline:\n{outline_str}")

        sections = self.split_by_headings(text, outline)
        result = self.process_sections(sections, outline, min_length, max_length)

        return [{'summary': r['summary'], 'content': r['content']} for r in result]

    def process_sections(self, sections, outline, min_split_length, max_split_length):
        """
        处理并合并Markdown段落，确保每个部分在指定长度范围内
        
        参数:
            sections: 原始分割的Markdown段落列表
            outline: Markdown大纲结构
            min_split_length: 最小分割长度
            max_split_length: 最大分割长度
            
        返回:
            处理后的段落列表，每个段落包含摘要和内容
        """
        preprocessed_sections = []  # 预处理后的段落列表
        current_section = None  # 当前正在处理的段落

        for section in sections:
            content_length = len(section['content'].strip())

            # 如果当前段落太短且有前一个段落，尝试合并
            if content_length < min_split_length and current_section is not None:
                # 合并内容，保留标题格式
                merged_content = f"{current_section['content']}\n\n{'#' * section['level']} {section['heading']}\n{section['content']}" if section.get('heading') else f"{current_section['content']}\n\n{section['content']}"

                # 检查合并后内容是否超过最大长度限制
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

            # 将当前段落添加到预处理列表
            if current_section:
                preprocessed_sections.append(current_section)
            
            # 开始处理新段落
            current_section = dict(section)
            if section.get('heading'):
                current_section['headings'] = [{'heading': section['heading'], 'level': section['level'], 'position': section['position']}]
            else:
                current_section['headings'] = []

        # 添加最后一个未处理的段落
        if current_section:
            preprocessed_sections.append(current_section)

        result = []
        accumulated_section = None

        for section in preprocessed_sections:
            content_length = len(section['content'].strip())

            # 二次处理：合并过短的段落
            if content_length < min_split_length:
                if not accumulated_section:
                    accumulated_section = dict(section)  # 初始化累积段落
                else:
                    accumulated_section['content'] += f"\n\n{'#' * section['level']} {section['heading']}\n{section['content']}" if section.get('heading') else f"\n\n{section['content']}"
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
                    summary = self.generate_enhanced_summary(accumulated_section, outline)
                    if accumulated_length > max_split_length:
                        sub_sections = self.split_long_section(accumulated_section, max_split_length)
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
                    accumulated_section = None
                continue

            if accumulated_section:
                summary = self.generate_enhanced_summary(accumulated_section, outline)
                accumulated_length = len(accumulated_section['content'].strip())
                if accumulated_length > max_split_length:
                    sub_sections = self.split_long_section(accumulated_section, max_split_length)
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
                accumulated_section = None

            # 处理过长的段落
            if content_length > max_split_length:
                sub_sections = self.split_long_section(section, max_split_length)  # 分割长段落
                for i, sub_content in enumerate(sub_sections):
                    summary = self.generate_enhanced_summary(section, outline, i + 1, len(sub_sections))
                    result.append({
                        'summary': summary,
                        'content': sub_content
                    })
            else:
                summary = self.generate_enhanced_summary(section, outline)
                content = f"{'#' * section['level']} {section['heading']}\n{section['content']}" if section.get('heading') else section['content']
                result.append({
                    'summary': summary,
                    'content': content
                })

        if accumulated_section:
            summary = self.generate_enhanced_summary(accumulated_section, outline)
            content = f"{'#' * accumulated_section['level']} {accumulated_section['heading']}\n{accumulated_section['content']}" if accumulated_section.get('heading') else accumulated_section['content']
            result.append({
                'summary': summary,
                'content': content
            })

        return result

    def extract_outline(self, text):
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

    def split_by_headings(self, text, outline):
        """
        根据标题将 Markdown 文本分割成多个部分。

        Args:
            text (str): 完整的 Markdown 文本内容。
            outline (list): 由 `extract_outline` 方法生成的大纲列表。

        Returns:
            list: 包含分割后内容的字典列表，每个字典包含：
                  - heading (str or None): 当前部分的标题文本，如果无标题则为 None。
                  - level (int): 当前部分的标题级别，如果无标题则为 0。
                  - content (str): 当前部分的文本内容。
                  - position (int): 当前部分在原始文本中的起始位置。
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

    def split_long_section(self, section, max_length):
        """
        将一个过长的部分分割成多个子部分，确保每个子部分不超过最大长度。
        尽量在句子或段落边界进行分割。

        Args:
            section (dict): 包含 'content' 的部分字典。
            max_length (int): 每个子部分的最大长度。

        Returns:
            list: 包含分割后子部分内容的列表。
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
                if item['title'] == heading_info['heading'] and item['level'] == heading_info['level']:
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
                for j in range(len(paths)):
                    unique_part = paths[j][len(prefix) + 3:] # +3 for ' > ['
                    summary += (', ' if j > 0 else '') + unique_part
                summary += ']'
                return summary

        # 如果没有找到共同前缀，则将所有路径用逗号连接
        return ', '.join(paths)

    def _generate_summary_for_multi_headings(self, section, outline, part_index, total_parts):
        """
        为包含多个子标题的段落生成摘要。

        Args:
            section (dict): 包含 'headings' 的部分字典。
            outline (list): 完整的文档大纲。
            part_index (int): 当前部分的索引。
            total_parts (int): 总部分数。

        Returns:
            str: 生成的摘要字符串。
        """
        headings_in_section = section.get('headings', [])
        if not headings_in_section:
            return self._format_summary_with_part_info(self._get_doc_title_prefix(outline) + " - 多个子标题段落", part_index, total_parts)

        # 提取所有标题文本并用 " - " 连接
        summary_parts = [h['heading'] for h in headings_in_section]
        base_summary = " - ".join(summary_parts)
        return self._format_summary_with_part_info(base_summary, part_index, total_parts)

    def _generate_summary_for_single_heading(self, section, outline, part_index, total_parts):
        """
        为包含单个标题的段落生成摘要。

        Args:
            section (dict): 包含 'heading' 的部分字典。
            outline (list): 完整的文档大纲。
            part_index (int): 当前部分的索引。
            total_parts (int): 总部分数。

        Returns:
            str: 生成的摘要字符串。
        """
        heading_path = self._build_heading_path(section, outline)
        if heading_path:
            base_summary = " - ".join(heading_path)
        else:
            base_summary = section.get('heading', '未命名段落')
        return self._format_summary_with_part_info(base_summary, part_index, total_parts)

    def generate_enhanced_summary(self, section, outline, part_num=None, total_parts=None):
        """
        为给定的部分生成增强的摘要。

        Args:
            section (dict): 包含 'content' 和 'headings' 的部分字典。
            outline (list): 完整的文档大纲。
            part_num (int, optional): 如果部分被分割，这是当前部分的编号。
            total_parts (int, optional): 如果部分被分割，这是总部分的数量。

        Returns:
            str: 生成的摘要字符串。
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