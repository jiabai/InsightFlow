import json
import requests

DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
API_KEY = ""
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"

def search_web(query: str) -> str:
    """模拟网络搜索工具"""
    return f"搜索结果：关于'{query}'的相关信息..."

def get_weather(location: str) -> str:
    """模拟天气查询工具"""
    return f"{location}的天气：晴天，温度25°C"

def call_openai_with_requests():
    # OpenAI API 配置
    api_key = API_KEY
    base_url = BASE_URL
    model = DEFAULT_MODEL

    # 请求头
    # headers = {
    #     "Authorization": f"Bearer {api_key}",
    #     "Content-Type": "application/json"
    # }
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://www.baidu.com", # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": "test", # Optional. Site title for rankings on openrouter.ai.
    }

    # 工具定义
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

    # 构造请求数据
    request_data = {
        "model": model,
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
    #     "model": "openai/gpt-oss-20b:free",
    #     "messages": [
    #         {
    #             "role": "user",
    #             "content": "What is the meaning of life?"
    #         }
    #     ]
    # }

    # 第一次API调用 - 让模型决定使用工具
    print("\n发送第一次请求...")
    response = requests.post(
        url=base_url,
        headers=headers,
        data=json.dumps(request_data),
        timeout=10
    )
    print(response.json())
    response.raise_for_status()
    result = response.json()
    print(f"\n第一次响应状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # # 检查是否有工具调用
    # message = result['choices'][0]['message']
    # if 'tool_calls' in message and message['tool_calls']:
    #     print("\n模型决定使用工具，执行工具调用...")

    #     # 添加助手的消息到对话历史
    #     request_data['messages'].append(message)

    #     # 执行工具调用
    #     for tool_call in message['tool_calls']:
    #         function_name = tool_call['function']['name']
    #         function_args = json.loads(tool_call['function']['arguments'])

    #         print(f"执行工具: {function_name}，参数: {function_args}")

    #         # 根据工具名称执行相应函数
    #         if function_name == "search_web":
    #             tool_result = search_web(function_args['query'])
    #         elif function_name == "get_weather":
    #             tool_result = get_weather(function_args['location'])
    #         else:
    #             tool_result = "未知工具"
            
    #         # 添加工具结果到对话历史
    #         request_data['messages'].append({
    #             "role": "tool",
    #             "tool_call_id": tool_call['id'],
    #             "content": tool_result
    #         })
        
    #     # 第二次API调用 - 基于工具结果生成最终回答
    #     print("\n发送第二次请求（包含工具结果）...")
        
    #     # 打印第二次请求的JSON
    #     second_json = json.dumps(request_data, ensure_ascii=False, indent=2)
    #     print("\n=== 第二次请求的完整JSON字符串 ===")
    #     print(second_json)
    #     print("=" * 50)
        
    #     second_response = requests.post(base_url, headers=headers, json=request_data)
    #     second_response.raise_for_status()
        
    #     final_result = second_response.json()
    #     print(f"\n第二次响应状态码: {second_response.status_code}")
    #     print(f"最终回答: {final_result['choices'][0]['message']['content']}")
    
    # else:
    #     print("\n模型没有使用工具，直接回答:")
    #     print(message['content'])

if __name__ == "__main__":
    call_openai_with_requests()
