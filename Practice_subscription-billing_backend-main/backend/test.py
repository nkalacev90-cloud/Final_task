print("Начало теста")

try:
    from database import engine, Base
    print("database импортирован")
    from models import Tariff
    print("models импортирован")
    print(Base.metadata.tables.keys())
except Exception as e:
    print("Ошибка:", e)