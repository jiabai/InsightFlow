import requests

user_id = "userid_123"
BASE_URL = "http://127.0.0.1:8000"
file_id = "fa43b6889c67ccb96dfcc6d06ad01602b4631a87521d3fd5fbc0bc4195d84372"

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
