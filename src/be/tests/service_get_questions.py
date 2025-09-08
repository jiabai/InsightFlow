import requests

FILE_ID = "3a8e2d0f03fcb4162c0d612f8e6e8f9b646ca2d61a30c8c10c7d51999085fc9f"
url_file_id = f"http://127.0.0.1:8000/questions/{FILE_ID}"

response = requests.get(url_file_id, timeout=10)
if response.status_code == 200:
    question_info = response.json()
    print(f"文件 {FILE_ID} 的问题列表:")
    for question in question_info['questions']:
        print(f"问题内容: {question['question']}, 标签: {question['label']}")
else:
    print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
