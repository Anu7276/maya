import os
import requests
import json

def test_maya():
    url = "http://127.0.0.1:5000/chat"
    api_key = os.getenv("GROQ_API_KEY", "")
    
    headers = {"Content-Type": "application/json"}
    
    # Test 1: Default (Hindi)
    print("\n--- Test 1: Hi (Expecting Hindi) ---")
    data = {
        "messages": [{"role": "user", "content": "Hi"}],
        "apiKey": api_key
    }
    response = requests.post(url, json=data, stream=True)
    full_text = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    chunk = json.loads(line_str[6:])
                    if "token" in chunk:
                        full_text += chunk["token"]
                except: pass
    print(f"Maya: {full_text}")

    # Test 2: Switch to English
    print("\n--- Test 2: English Question (Expecting English) ---")
    data["messages"].append({"role": "assistant", "content": full_text})
    data["messages"].append({"role": "user", "content": "What is the capital of Japan?"})
    response = requests.post(url, json=data, stream=True)
    full_text_en = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    chunk = json.loads(line_str[6:])
                    if "token" in chunk:
                        full_text_en += chunk["token"]
                except: pass
    print(f"Maya: {full_text_en}")

    # Test 3: Switch back to Hindi
    print("\n--- Test 3: Aap kaise ho? (Expecting Hindi) ---")
    data["messages"].append({"role": "assistant", "content": full_text_en})
    data["messages"].append({"role": "user", "content": "Aap kaise ho?"})
    response = requests.post(url, json=data, stream=True)
    full_text_hi = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    chunk = json.loads(line_str[6:])
                    if "token" in chunk:
                        full_text_hi += chunk["token"]
                except: pass
    print(f"Maya: {full_text_hi}")

if __name__ == "__main__":
    test_maya()
