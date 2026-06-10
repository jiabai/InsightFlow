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

        # LLM 配置（从环境变量读取，不设默认密钥）
        self.llm_config = {
            'provider': os.getenv('LLM_PROVIDER', 'siliconflow'),
            'api_key': os.getenv('LLM_API_KEY'),
            'base_url': os.getenv('LLM_API_URL', 'https://api.siliconflow.cn/v1'),
            'model': os.getenv('LLM_MODEL', 'Qwen/Qwen3-30B-A3B-Instruct-2507')
        }

        # 项目配置
        self.project_config = {
            'questionGenerationLength': 1000,
            'questionMaskRemovingProbability': 0,
            'language': '中文'
        }

        self.project_details = {'globalPrompt': '', 'questionPrompt': ''}
