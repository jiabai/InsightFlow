import logging
from be.common.logger_config import setup_logging

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)

from .llm_config_manager import LLMConfigManager

class LLMClient:
    """
    一个通用的 LLM 客户端，用于与不同提供商的语言模型进行交互。
    """
    def __init__(self, config):
        """
        初始化 LLMClient。

        Args:
            config (dict): 包含 LLM 提供商配置的字典，
                           需要包含 'provider', 'api_key', 'base_url', 和 'model'。
        """
        self.config_manager = LLMConfigManager(config)
        self.client = self.config_manager.get_client()
        self.model = self.config_manager.model

    def get_response(self, prompt, stream=False, **kwargs):
        """
        获取 LLM 的响应。

        Args:
            prompt (str): 发送给 LLM 的提示。
            stream (bool): 是否以流式模式获取响应。默认为 False。
            **kwargs: 其他传递给 LLM API 的参数。

        Returns:
            str or generator or None: 如果 stream 为 False，返回字符串响应。
                                     如果 stream 为 True，返回一个响应生成器。
                                     如果发生错误，返回 None。
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                stream=stream,
                **kwargs
            )
            if stream:
                return chat_completion
            else:
                return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
            return None