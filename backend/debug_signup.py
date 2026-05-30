import requests

response = requests.post(
    'http://localhost:8000/auth/signup',
    json={'email': 'debug@test.com', 'password': 'pass123'}
)

print(f"Status: {response.status_code}")
print(f"Raw Response: {response.text}")