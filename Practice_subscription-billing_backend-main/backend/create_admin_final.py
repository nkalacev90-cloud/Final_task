from database import SessionLocal
from models import User
import bcrypt

db = SessionLocal()

# Удаляем старого админа
db.query(User).filter(User.email == "admin@billing.local").delete()
db.commit()

# Хешируем пароль
password = "admin123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

admin = User(
    email="admin@billing.local",
    hashed_password=hashed,
    is_admin=True
)
db.add(admin)
db.commit()

print("✅ Админ создан!")
print(f"Email: admin@billing.local")
print(f"Пароль: admin123")

db.close()