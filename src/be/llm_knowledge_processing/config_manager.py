"""
Configuration management module for the LLM knowledge processing system.

This module provides centralized configuration management through the ConfigManager class,
handling file paths, LLM settings, and project-specific configurations.
"""

import os

class ConfigManager:
    """
    集中管理所有配置的类
    """
    def __init__(self):
        # 目录配置
        self.base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )
        self.upload_dir = os.path.join(self.base_dir, 'upload_file')
        self.completed_dir = os.path.join(self.base_dir, 'completed')

        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.completed_dir, exist_ok=True)

        # LLM 配置
        self.llm_config = {
            'provider': 'siliconflow',
            'api_key': 'sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf',
            'base_url': 'https://api.siliconflow.cn/v1',
            'model': 'Qwen/Qwen3-30B-A3B-Instruct-2507'
        }

        # 项目配置
        self.project_config = {
            'questionGenerationLength': 1000,
            'questionMaskRemovingProbability': 0,
            'language': '中文'
        }

        self.project_details = {'globalPrompt': '', 'questionPrompt': ''}
