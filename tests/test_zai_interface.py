from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="")

messages = [
    {
        "role": "system",
        "content": "你是一个专业的金融分析师，擅长分析和总结财经事件、政策变化和市场数据。"
    },
    {
        "role": "user",
        "content": "2025年8月的重要财经事件、政策变化和市场数据"
    }
]

response = client.chat.completions.create(
    model="glm-4.5",
    messages=messages,
    temperature=0.4,
    stream=False
)

print(response.choices[0].message.content)
