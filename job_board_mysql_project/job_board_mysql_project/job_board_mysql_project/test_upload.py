import requests
from pathlib import Path

BASE = 'http://127.0.0.1:5000'

def main():
    s = requests.Session()

    # Register a test student
    reg = s.post(f'{BASE}/register', data={
        'username': 'test_student',
        'email': 'test_student@example.com',
        'password': 'password123',
        'role': 'student'
    })
    print('register', reg.status_code)
    print(reg.text[:2000])

    # Login
    lg = s.post(f'{BASE}/login', data={
        'email': 'test_student@example.com',
        'password': 'password123'
    })
    print('login', lg.status_code)
    print(lg.text[:2000])

    # Upload profile with resume
    files = {'resume': ('test_resume.txt', open('test_resume.txt','rb'))}
    data = {'phone': '123-456-7890', 'bio': 'I am a test student.'}
    resp = s.post(f'{BASE}/profile', data=data, files=files)
    print('profile upload', resp.status_code)
    print(resp.text[:400])

if __name__ == '__main__':
    main()
