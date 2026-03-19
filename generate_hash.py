from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = "admin123"

hashed = pwd.hash(password)

print("YOUR HASH:")
print(hashed)
