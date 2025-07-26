import hashlib
import requests

user_id = "userid_123"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
file_id = "7f8458b670fb5467157a1696457d48e7041d27cc9209278c060c5b5b37fa55bb"
download_url = f"http://127.0.0.1:8000/download/{user_id}/{file_id}"
filename_url = f"http://127.0.0.1:8000/files/{user_id}/{file_id}"

response = requests.get(filename_url, timeout=10)
filename = response.json()["filename"]

response = requests.get(download_url, timeout=10)
if response.status_code == 200:
    print("文件下载成功！")
    with open(f"{filename}", "wb") as f:
        f.write(response.content)
else:
    print(f"文件下载失败，状态码: {response.status_code}")
    print(response.text)
