import requests
import hashlib

user_id = "userid_123"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
BASE_URL = "http://127.0.0.1:8000"
file_id = "3a8e2d0f03fcb4162c0d612f8e6e8f9b646ca2d61a30c8c10c7d51999085fc9f"

delete_url = f"{BASE_URL}/delete/{user_id}/{file_id}"

try:
    response = requests.delete(delete_url, timeout=30)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except requests.exceptions.JSONDecodeError as e:
        print(f"Response解析失败: {e}, 原始内容: {response.text}")
    response.raise_for_status()  # 如果请求失败，抛出 HTTPError
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
