from database import SessionLocal, engine, Base
from models import User, Tariff, Subscription, Payment
from auth import get_password_hash

def clear_db():
    db = SessionLocal()
    
    print("🗑️  Удаляем все данные...")
    
    # Удаляем в правильном порядке (сначала дочерние таблицы)
    db.query(Payment).delete()
    db.query(Subscription).delete()
    db.query(User).delete()
    db.query(Tariff).delete()
    
    db.commit()
    print("✅ Все данные удалены")
    
    # Создаём админа
    print("👤 Создаём админа...")
    hashed = get_password_hash("admin123")
    admin = User(
        email="admin@billing.local",
        hashed_password=hashed,
        is_admin=True
    )
    db.add(admin)
    db.commit()
    print("✅ Админ создан: admin@billing.local / admin123")
    
    # Создаём базовые тарифы
    print("📦 Создаём базовые тарифы...")
    tariffs = [
        Tariff(name="Старт", price=490.00, period_months=1, trial_days=0),
        Tariff(name="Бизнес", price=1490.00, period_months=1, trial_days=14),
    ]
    for t in tariffs:
        db.add(t)
    db.commit()
    print("✅ Тарифы созданы")
    
    db.close()
    print("\n🎉 База данных готова к работе!")

if __name__ == "__main__":
    clear_db()