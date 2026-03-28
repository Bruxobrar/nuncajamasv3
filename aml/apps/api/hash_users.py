from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
import json
users = {
    'admin': pwd_context.hash('admin123'),
    'user': pwd_context.hash('user123')
}
with open('users.json', 'w') as f:
    json.dump(users, f, indent=2)
print('users.json updated with hashed passwords')