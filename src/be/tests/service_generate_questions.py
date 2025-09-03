import hashlib
import requests

user_id = "userid_456"
file_id = "2bc007b6bbfa4e98f943ac7c9f394fe3bf595d5da2dc067c2efc6e86863b6f08"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
url = f"http://127.0.0.1:8000/questions/generate/{user_id}/{file_id}"

response = requests.post(url, timeout=10)

if response.status_code == 200:
    print("问题生成成功！")
    print(response.json())
else:
    print(f"问题生成失败，状态码: {response.status_code}")
    print(response.text)
