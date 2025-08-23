import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_MODEL = "Qwen/Qwen3-8B"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"

model = DEFAULT_MODEL
messages = [
    {
        "role": "user",
        "content": "你好"
    }
]
max_tokens = 4096
temperature = 0.7
headers = {
    "Authorization": "Bearer <API_KEY>",
    "Content-Type": "application/json"
}


# 配置重试策略
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
    backoff_factor=1
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

data = {
    "model": model,
    "messages": messages,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "stream": False
}

try:
    response = session.post(
        BASE_URL,
        json=data,
        headers=headers,
        timeout=(30, 120)  # (连接超时, 读取超时)
    )
    response.raise_for_status()
    res = response.json()['choices'][0]['message']['content']
    print(res)
except requests.exceptions.Timeout:
    raise Exception("请求超时，请检查网络连接或稍后重试")
except requests.exceptions.ConnectionError:
    raise Exception("网络连接错误，请检查网络设置")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 503:
        raise Exception("API 服务暂时不可用，请稍后重试")
    else:
        raise Exception(f"HTTP 错误: {e.response.status_code}")
