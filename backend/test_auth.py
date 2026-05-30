import requests

r = requests.post('http://localhost:8000/auth/signup', json={'email': 'test@test.com', 'password': 'pass123'})
print(r.json())