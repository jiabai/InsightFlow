import requests

FILE_ID = "a0b111ca3407ff23e269215869205257c1a0235d8376ff4678784bf367d8ae0b"
url_file_id = f"http://127.0.0.1:8000/questions/{FILE_ID}"

response = requests.get(url_file_id, timeout=10)
if response.status_code == 200:
    question_info = response.json()
    print(f"文件 {FILE_ID} 的问题列表:")
    for question in question_info['questions']:
        print(f"问题内容: {question['question']}, 标签: {question['label']}")
else:
    print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
