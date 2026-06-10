import logging
import asyncio

logger = logging.getLogger(__name__)


class LLMClient:
    """Multi-provider LLM client.

    Configuration dict keys: provider, api_key, base_url, model.
    Supported providers: openai, ollama, zhipu, siliconflow.
    """

    def __init__(self, config: dict, is_mock: bool = False):
        provider = config.get("provider", "openai")
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        self.model = config.get("model")
        self.is_mock = is_mock

        if provider == "openai" or provider == "siliconflow":
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif provider == "ollama":
            from ollama import Client
            self.client = Client(host=base_url)
        elif provider == "zhipu":
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def get_response(self, prompt, stream=False, **kwargs):
        if self.is_mock:
            logger.info("Mocking LLM response for prompt: %s", prompt)
            return "This is a mock response for: " + prompt

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                stream=stream,
                **kwargs
            )
            if stream:
                return chat_completion
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error("An error occurred: %s", e, exc_info=True)
            return None

    async def get_response_async(self, prompt, stream=False, **kwargs):
        if self.is_mock:
            await asyncio.sleep(0.1)
            return "This is a mock response for: " + prompt

        try:
            chat_completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                stream=stream,
                **kwargs
            )
            if stream:
                return chat_completion
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error("An error occurred: %s", e, exc_info=True)
            return None
