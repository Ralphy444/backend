import requests
import json

# Test login API
url = "http://192.168.1.31:8000/api/auth/login/"

test_credentials = [
    {"username": "hanz", "password": "admin123"},
    {"username": "ralphy", "password": "admin123"},
    {"username": "rasta", "password": "admin123"},
]

print("Testing API Login Endpoint")
print("="*80)

for cred in test_credentials:
    try:
        response = requests.post(url, json=cred, timeout=5)
        if response.status_code == 200:
            print(f"SUCCESS: {cred['username']} - Status {response.status_code}")
        else:
            print(f"FAILED: {cred['username']} - Status {response.status_code}")
            print(f"  Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {url}")
        print("  Make sure Django server is running: python manage.py runserver 0.0.0.0:8000")
        break
    except Exception as e:
        print(f"ERROR: {str(e)}")
        break

print("="*80)
