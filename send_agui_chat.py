import requests
import json
import uuid

url = "http://localhost:8000/api/ag_ui/chat"
headers = {"Content-Type": "application/json"}
payload = {
  "thread_id": "test-thread-123",
  "run_id": "test-run-456",
  "messages": [
    {
      "id": str(uuid.uuid4()), # Generate a unique ID for the message
      "role": "user",
      "content": "Hello agent, what can you do?"
    }
  ],
  "state": {}, 
  "tools": [], 
  "context": [], 
  "forwarded_props": {} 
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True)
    response.raise_for_status() # Raise an exception for HTTP errors

    print("Streaming response:")
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            print(chunk.decode('utf-8'), end='')

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
    if e.response is not None:
        print(f"Response status code: {e.response.status_code}")
        print(f"Response body: {e.response.text}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")