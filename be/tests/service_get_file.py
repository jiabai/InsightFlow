import requests

USER_ID = "userid_123"
SKIP = 0
LIMIT = 10
url_with_pagination = f"http://127.0.0.1:8000/files/{USER_ID}?skip={SKIP}&limit={LIMIT}"

response = requests.get(url_with_pagination, timeout=10)

if response.status_code == 200:
    files_info = response.json()
    if files_info:
        print(f"用户 {USER_ID} 的文件列表 (跳过 {SKIP} 条，限制 {LIMIT} 条):")
        for file in files_info:
            print(f"文件id：{file['id']}, "
                  f"文件名: {file['filename']}, "
                  f"大小: {file['file_size']} bytes, "
                  f"上传时间: {file['upload_time']}")
    else:
        print(f"用户 {USER_ID} 没有找到文件或分页参数超出范围。")
else:
    print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
