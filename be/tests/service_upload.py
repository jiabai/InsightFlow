import os
import hashlib
import requests

user_id = "userid_123"
user_id = hashlib.sha256(user_id.encode()).hexdigest()
url = f"http://192.168.31.233:8000/upload/{user_id}"
file_path = os.path.join("D:", "VSCode", "notes", "Effectiveness of Advertising Campaigns on Short-Form Video Social Platforms.md")  # 要上传的文件路径

with open(file_path, "rb") as f:
    import os
    files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
    response = requests.post(url, files=files, timeout=10)

if response.status_code == 200:
    print("文件上传成功！")
    print(response.json())
else:
    print(f"文件上传失败，状态码: {response.status_code}")
    print(response.text)
