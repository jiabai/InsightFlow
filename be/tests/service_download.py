import requests

user_id = "userid_123"
file_id = "fa43b6889c67ccb96dfcc6d06ad01602b4631a87521d3fd5fbc0bc4195d84372"
url = f"http://127.0.0.1:8000/download/{user_id}/{file_id}"

response = requests.get(url, timeout=10)

if response.status_code == 200:
    print("文件下载成功！")
    with open(f"{file_id}.pdf", "wb") as f:
        f.write(response.content)
else:
    print(f"文件下载失败，状态码: {response.status_code}")
    print(response.text)
