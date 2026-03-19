import os
import requests
import json
import time

url = "http://127.0.0.1:5000/chat"
payload = {
    "messages": [{"role": "user", "content": "search for weather in Mumbai"}],
    "apiKey": os.getenv("GROQ_API_KEY", ""),
    "user_id": "anurag_dev"
}

print(f"Testing: {payload['messages'][0]['content']}")
try:
    response = requests.post(url, json=payload, stream=True)
    print(f"Status: {response.status_code}")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('event: '):
                event = decoded_line[7:]
                print(f"\n[EVENT: {event}]")
            elif decoded_line.startswith('data: '):
                data = decoded_line[6:]
                print(f"DATA: {data[:100]}...")
except Exception as e:
    print(f"Error: {e}")
