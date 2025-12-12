import http.client, json

conn = http.client.HTTPConnection('localhost', 8000, timeout=10)
payload = {
    'username': 'adminuser2',
    'email': 'admin2@example.com',
    'password': 'admin123',
    'admin_code': 'MakeMeAdmin123'
}
headers = {'Content-Type': 'application/json'}
body = json.dumps(payload)
print('Sending body:', body)
conn.request('POST', '/register', body, headers)
res = conn.getresponse()
print('Status', res.status)
data = res.read().decode()
print('Response:', data)
