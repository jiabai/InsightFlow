import requests

FILE_ID = "d7521ddcdff89b8b5608827fc0d9592a6f02a72ea616ee082afef458359bab62"
# url_file_id = f"http://192.168.31.233:8000/file_status/{FILE_ID}"
url_file_id = f"http://39.107.59.41:18080/file_status/{FILE_ID}"

response = requests.get(url_file_id, timeout=10)
if response.status_code == 200:
    question_info = response.json()
    print(f"文件 {FILE_ID} 的redis状态: {question_info}")
else:
    print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
