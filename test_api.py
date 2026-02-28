import requests
import time
import json

URL = "http://127.0.0.1:8000/review-code"

payload = {
    "code": """def add(a, b):
    return a +

print(add(5, 3))""",
    "language": "Python"
}

try:
    print("Sending request to API...\n")
    start_time = time.time()
    response = requests.post(URL, json=payload)
    end_time = time.time()

    print("Status Code:", response.status_code)
    print("Response Time:", round(end_time - start_time, 2), "seconds\n")
    print("Response JSON:\n")
    print(json.dumps(response.json(), indent=4))

except Exception as e:
    print("Error:", e)
