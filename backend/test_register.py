import requests
import json

url = "http://localhost:8000/api/v1/auth/register"
data = {
    "email": "swastikaoa@gmail.com",
    "password": "testpassword123",
    "full_name": "miko"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
