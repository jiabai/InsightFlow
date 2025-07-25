import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from be.llm_knowledge_processing.llm_client import LLMClient



llm_config = {
    'provider': 'siliconflow',
    'api_key': 'sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf',
    'base_url': 'https://api.siliconflow.cn/v1',
    'model': 'Qwen/Qwen3-8B'
}

llm_client = LLMClient(llm_config, is_mock=False)
raw_response = llm_client.get_response(prompt="你好", stream=False)
print(raw_response)
