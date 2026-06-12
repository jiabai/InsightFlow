import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv

from server.llm_knowledge_processing.llm_client import LLMClient

# Load shared config from src/.env — never hardcode credentials in source.
_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=_env_path)

llm_config = {
    'provider': os.getenv('LLM_PROVIDER', 'siliconflow'),
    'api_key': os.getenv('LLM_API_KEY'),
    'base_url': os.getenv('LLM_API_URL', 'https://api.siliconflow.cn/v1'),
    'model': os.getenv('LLM_MODEL', 'Qwen/Qwen3-8B'),
}

if not llm_config['api_key']:
    raise SystemExit('LLM_API_KEY is not set — populate src/.env before running this test.')

llm_client = LLMClient(llm_config, is_mock=False)
raw_response = llm_client.get_response(prompt="你好", stream=False)
print(raw_response)
