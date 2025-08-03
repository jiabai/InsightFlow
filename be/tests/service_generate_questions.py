import hashlib
import requests

user_id = "userid_123"
file_id = "d7521ddcdff89b8b5608827fc0d9592a6f02a72ea616ee082afef458359bab62"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
url = f"http://127.0.0.1:8000/questions/generate/{user_id}/{file_id}"

response = requests.post(url, timeout=10)

if response.status_code == 200:
    print("问题生成成功！")
    print(response.json())
else:
    print(f"问题生成失败，状态码: {response.status_code}")
    print(response.text)
