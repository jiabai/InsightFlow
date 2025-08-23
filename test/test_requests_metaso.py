import requests
import json

url = "https://metaso.cn/api/v1/chat/completions"
payload = json.dumps({"q": "谁是这个世界上最美丽的女人", "model": "fast", "format": "simple"})
headers = {
  'Authorization': 'Bearer <API_KEY>',
  'Accept': 'application/json',
  'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
print("---------------------------")
# 解析 JSON 响应
response_json = json.loads(response.text)
# 提取回答内容
answer = response_json['answer']
print("回答:", answer)
