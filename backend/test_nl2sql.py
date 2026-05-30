import requests
import json

BASE = 'http://localhost:8000'

# 1. Signup
print("1. Signing up...")
signup = requests.post(f'{BASE}/auth/signup', json={
    'email': 'nltest@test.com',
    'password': 'pass123'
})
token = signup.json()['token']
print(f"Token: {token[:20]}...")

# 2. Create sample CSV
print("\n2. Creating sample CSV...")
csv_data = """product,sales,region
apple,1000,north
banana,800,south
orange,1200,north
grape,600,east"""

with open('sample.csv', 'w') as f:
    f.write(csv_data)

# 3. Upload
print("3. Uploading CSV...")
with open('sample.csv', 'rb') as f:
    files = {'file': f}
    headers = {'Authorization': f'Bearer {token}'}
    upload = requests.post(f'{BASE}/files/upload', files=files, headers=headers)

file_id = upload.json()['file_id']
print(f"File ID: {file_id}")

# 4. Ask question
print("\n4. Asking question...")
question = "What is the total sales?"
query = requests.post(
    f'{BASE}/query/ask',
    json={'file_id': file_id, 'question': question},
    headers={'Authorization': f'Bearer {token}'}
)

result = query.json()
print(f"\nQuestion: {result['question']}")
print(f"SQL: {result['sql']}")
print(f"Data: {json.dumps(result['data'], indent=2)}")
