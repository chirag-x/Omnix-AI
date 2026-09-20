import requests
url = "http://localhost:20128/v1/chat/completions"
headers = {"Authorization": "Bearer sk-91d3746c342d6cf3-ba40b7-c856582b", "Content-Type": "application/json"}
payload = {"model": "antigravity/gemini-3.6-flash-high", "messages": [{"role": "user", "content": "test"}], "temperature": 0, "stream": False}
r = requests.post(url, headers=headers, json=payload)
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")
