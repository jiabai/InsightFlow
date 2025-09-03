import requests
import json

DEFAULT_MODEL = "z-ai/glm-4.5-air:free"
API_KEY = "<API_KEY>"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索网络信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定地点的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

request_data = {
    "model": DEFAULT_MODEL,
    "messages": [
        {
            "role": "system",
            "content": "你是一个有用的AI助手，可以使用提供的工具来回答用户问题。"
        },
        {
            "role": "user",
            "content": "请帮我搜索一下人工智能的最新发展，然后告诉我北京的天气如何？"
        }
    ],
    "tools": tools,
    "tool_choice": "auto",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": False
}
# request_data = {
#     "model": DEFAULT_MODEL,
#     "messages": [
#       {
#         "role": "user",
#         "content": "What is the meaning of life?"
#       }
#     ]
# }

response = requests.post(
  url=BASE_URL,
  headers={
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://www.baidu.com", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "test", # Optional. Site title for rankings on openrouter.ai.
  },
  data=json.dumps(request_data),
  timeout=10
)

print(response.json())
