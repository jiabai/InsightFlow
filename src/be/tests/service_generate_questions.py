import hashlib
import requests

user_id = "userid_123"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
file_id = "3a8e2d0f03fcb4162c0d612f8e6e8f9b646ca2d61a30c8c10c7d51999085fc9f"
url = f"http://127.0.0.1:8000/questions/generate/{user_id}/{file_id}"

response = requests.post(url, timeout=10)

if response.status_code == 200:
    print("问题生成成功！")
    print(response.json())
else:
    print(f"问题生成失败，状态码: {response.status_code}")
    print(response.text)
