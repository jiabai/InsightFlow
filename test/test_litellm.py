import litellm

response = litellm.completion(
    model="openai/glm-4.5",
    api_key="<API_KEY>",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    messages=[
                {
                    "role": "user",
                    "content": "Hey, how's it going?",
                }
    ],
)
print(response)
