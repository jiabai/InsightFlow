class LLMConfigManager:
    """
    管理 LLM 配置并根据提供商创建相应的客户端实例。
    """
    def __init__(self, config):
        """
        初始化 LLMConfigManager。

        Args:
            config (dict): 包含 LLM 提供商配置的字典，
                           需要包含 'provider', 'api_key', 'base_url', 和 'model'。
        """
        self.provider = config.get('provider', 'openai')
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        self.model = config.get('model')

    def get_client(self):
        """
        根据配置的提供商获取相应的 LLM 客户端。

        Returns:
            object: 特定提供商的客户端实例。

        Raises:
            ValueError: 如果提供商不受支持。
        """
        if self.provider == 'openai':
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.provider == 'ollama':
            from ollama import Client
            return Client(host=self.base_url)
        elif self.provider == 'zhipu':
            from zhipuai import ZhipuAI
            return ZhipuAI(api_key=self.api_key)
        elif self.provider == 'siliconflow':
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")