import requests

FILE_ID = "7f8458b670fb5467157a1696457d48e7041d27cc9209278c060c5b5b37fa55bb"
url_file_id = f"http://127.0.0.1:8000/file_status/{FILE_ID}"

response = requests.get(url_file_id, timeout=10)
if response.status_code == 200:
    question_info = response.json()
    print(f"文件 {FILE_ID} 的redis状态: {question_info}")
else:
    print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
