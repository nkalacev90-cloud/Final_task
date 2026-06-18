from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timedelta
from typing import Optional, List

from database import SessionLocal, engine, Base
from models import User, Tariff, Subscription, Payment
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_admin
)
from scheduler import scheduler  # Импортируем планировщик
from models import User, Tariff, Subscription, Payment, TrialUsage

# ========== 1. СОЗДАЁМ APP ==========
app = FastAPI(title="Billing System API", version="1.0.0")

# ========== 2. ДОБАВЛЯЕМ CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # разрешаем все источники (для разработки)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 3. СОЗДАЁМ ТАБЛИЦЫ ==========
Base.metadata.create_all(bind=engine)

# ========== 4. КОРЕНЬ ==========
@app.get("/")
def root():
    return {"message": "Сервер работает!"}

# ========== 5. ФУНКЦИЯ ДЛЯ БД ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== 6. АУТЕНТИФИКАЦИЯ ==========

@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    hashed = get_password_hash(password)
    user = User(email=email, hashed_password=hashed, is_admin=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Пользователь создан", "user_id": user.id}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Вход и получение JWT-токена"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return {"id": current_user.id, "email": current_user.email, "is_admin": current_user.is_admin}

# ========== 7. ТАРИФЫ ==========

@app.get("/tariffs")
def get_tariffs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Получить список всех тарифов"""
    tariffs = db.query(Tariff).filter(Tariff.is_archived == False).all()
    return tariffs

@app.post("/tariffs")
def create_tariff(
    name: str,
    price: float,
    period_months: int = 1,
    trial_days: int = 0,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Создать новый тариф (только админ)"""
    tariff = Tariff(
        name=name,
        price=price,
        period_months=period_months,
        trial_days=trial_days
    )
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return tariff

@app.delete("/tariffs/{tariff_id}")
def archive_tariff(
    tariff_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Архивировать тариф (только админ)"""
    tariff = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    tariff.is_archived = True
    db.commit()
    return {"message": "Тариф архивирован"}

# ========== 8. ПОДПИСКИ ==========

@app.post("/subscriptions")
def create_subscription(
    tariff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tariff = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    
    # Проверка на активную подписку
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(["active", "trial", "paused"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка")
    
    # ========== НОВОЕ: проверка на повторное использование пробного периода ==========
    if tariff.trial_days > 0:
        trial_used = db.query(TrialUsage).filter(
            TrialUsage.user_id == current_user.id,
            TrialUsage.tariff_id == tariff_id
        ).first()
        
        if trial_used:
            # Пробный период уже был использован — даём подписку без триала
            now = datetime.utcnow()
            subscription = Subscription(
                user_id=current_user.id,
                tariff_id=tariff_id,
                status="active",  # сразу активна, без пробного
                start_date=now,
                next_billing_date=now + timedelta(days=30 * tariff.period_months)
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            # Сразу создаём платёж
            payment = Payment(
                subscription_id=subscription.id,
                amount=tariff.price,
                status="paid",
                tariff_name=tariff.name,
                description="Оформление подписки (повторно, без пробного периода)"
            )
            db.add(payment)
            db.commit()
            
            return {
                "subscription": subscription,
                "message": "Подписка оформлена без пробного периода (он уже был использован)"
            }
    
    # ========== Обычное оформление (с пробным или без) ==========
    now = datetime.utcnow()
    trial_end = now + timedelta(days=tariff.trial_days) if tariff.trial_days > 0 else None
    next_billing = trial_end if trial_end else now + timedelta(days=30 * tariff.period_months)
    
    subscription = Subscription(
        user_id=current_user.id,
        tariff_id=tariff_id,
        status="trial" if tariff.trial_days > 0 else "active",
        start_date=now,
        trial_end_date=trial_end,
        next_billing_date=next_billing
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Если пробный период есть — записываем, что он использован
    if tariff.trial_days > 0:
        trial_usage = TrialUsage(user_id=current_user.id, tariff_id=tariff_id)
        db.add(trial_usage)
        db.commit()
    
    # Если нет пробного периода — сразу списываем
    if tariff.trial_days == 0:
        payment = Payment(
            subscription_id=subscription.id,
            amount=tariff.price,
            status="paid",
            tariff_name=tariff.name,
            description="Первое списание при оформлении подписки"
        )
        db.add(payment)
        db.commit()
    
    return subscription

@app.get("/subscriptions/me")
def get_my_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Получить текущую подписку пользователя"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    # Подгружаем тариф
    tariff = db.query(Tariff).filter(Tariff.id == subscription.tariff_id).first()
    
    # Возвращаем с вложенным объектом tariff
    return {
        "id": subscription.id,
        "user_id": subscription.user_id,
        "tariff_id": subscription.tariff_id,
        "tariff": {"id": tariff.id, "name": tariff.name, "price": tariff.price} if tariff else None,
        "status": subscription.status,
        "start_date": subscription.start_date,
        "next_billing_date": subscription.next_billing_date,
        "trial_end_date": subscription.trial_end_date,
        "end_date": subscription.end_date,
        "auto_renew": subscription.auto_renew,
        "retry_count": subscription.retry_count,
        "next_retry_date": subscription.next_retry_date,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at
    }

@app.put("/subscriptions/{subscription_id}/cancel")
def cancel_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отменить подписку"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    if subscription.status not in ["active", "trial"]:
        raise HTTPException(status_code=400, detail="Подписка уже неактивна или отменена")
    
    subscription.status = "cancelled"
    db.commit()
    return {"message": "Подписка отменена", "subscription": subscription}

# ========== 9. ПЛАТЕЖИ ==========

@app.post("/payments")
def create_payment(
    subscription_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать платёж (списание)"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    payment = Payment(
        subscription_id=subscription_id,
        amount=amount,
        status="paid"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

@app.get("/payments")
def get_payments(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить историю платежей по подписке (сортировка по дате: сначала новые)"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    # Сортировка: сначала самые свежие (DESC)
    payments = db.query(Payment).filter(
        Payment.subscription_id == subscription_id
    ).order_by(Payment.payment_date.desc()).all()  # <-- добавлено order_by
    
    return payments

# ========== 10. СМЕНА ТАРИФА (FR-23) ==========

@app.put("/subscriptions/{subscription_id}/change-tariff")
def change_tariff(
    subscription_id: int,
    new_tariff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Смена тарифа с пропорциональным пересчётом (FR-23)"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")

    new_tariff = db.query(Tariff).filter(Tariff.id == new_tariff_id).first()
    if not new_tariff:
        raise HTTPException(status_code=404, detail="Новый тариф не найден")

    old_tariff = db.query(Tariff).filter(Tariff.id == subscription.tariff_id).first()
    if not old_tariff:
        raise HTTPException(status_code=404, detail="Старый тариф не найден")

    now = datetime.utcnow()
    next_billing = subscription.next_billing_date
    total_period_days = old_tariff.period_months * 30
    days_remaining = (next_billing - now).days
    if days_remaining < 0:
        days_remaining = 0
    
    old_price = old_tariff.price
    new_price = new_tariff.price
    
    refund = (days_remaining / total_period_days) * old_price
    extra_charge = ((total_period_days - days_remaining) / total_period_days) * new_price
    difference = extra_charge - refund
    
    # ========== ОБНОВЛЯЕМ ПОДПИСКУ ==========
    subscription.tariff_id = new_tariff_id
    subscription.updated_at = now
    
    # ========== ВАЖНО: сбрасываем пробный период ==========
    # У нового тарифа НЕТ пробного периода при смене
    subscription.trial_end_date = None
    subscription.status = "active"  # при смене тарифа подписка становится активной
    
    # Создаём запись о пересчёте
    payment = Payment(
        subscription_id=subscription.id,
        amount=abs(difference),
        status="prorated",
        tariff_name=f"{old_tariff.name} → {new_tariff.name}",
        description="Пропорциональный пересчёт при смене тарифа"
    )
    db.add(payment)
    db.commit()
    db.refresh(subscription)
    
    return {
        "message": "Тариф успешно изменён",
        "subscription": subscription,
        "proration": {
            "refund": refund,
            "extra_charge": extra_charge,
            "difference": difference,
            "days_remaining": days_remaining
        }
    }

# ========== 11. АДМИНКА ==========

@app.get("/admin/subscriptions")
def admin_subscriptions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Просмотр всех подписок (только админ)"""
    subscriptions = db.query(Subscription).all()
    return subscriptions

@app.get("/admin/revenue")
def admin_revenue(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Отчёт по выручке за период с группировкой по месяцам (только админ)"""
    query = db.query(Payment).filter(Payment.status == "paid")
    
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    
    payments = query.all()
    total_revenue = sum(float(p.amount) for p in payments)
    
    # Группировка по месяцам
    monthly_data = {}
    for p in payments:
        month_key = p.payment_date.strftime("%Y-%m")
        month_name = p.payment_date.strftime("%b %Y")
        if month_key not in monthly_data:
            monthly_data[month_key] = {"month": month_name, "total": 0, "count": 0}
        monthly_data[month_key]["total"] += float(p.amount)
        monthly_data[month_key]["count"] += 1
    
    monthly_list = [{"month": v["month"], "total": v["total"], "count": v["count"]} 
                    for k, v in sorted(monthly_data.items())]
    
    return {
        "total_revenue": total_revenue,
        "payments_count": len(payments),
        "start_date": start_date,
        "end_date": end_date,
        "monthly": monthly_list
    }

@app.put("/admin/subscriptions/{subscription_id}/pause")
def admin_pause_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Ручная приостановка подписки (только админ)"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    subscription.status = "paused"
    db.commit()
    return {"message": "Подписка приостановлена", "subscription": subscription}

@app.put("/admin/subscriptions/{subscription_id}/cancel")
def admin_cancel_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Ручная отмена подписки (только админ)"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    subscription.status = "cancelled"
    db.commit()
    return {"message": "Подписка отменена", "subscription": subscription}

@app.post("/admin/run-dunning")
def run_dunning(admin: User = Depends(get_current_admin)):
    """Запуск Dunning-процесса вручную (только админ)"""
    from scheduler import process_dunning
    process_dunning()
    return {"message": "Dunning-процесс запущен"}

@app.put("/subscriptions/{subscription_id}/pause")
def pause_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    if subscription.status != "active":
        raise HTTPException(status_code=400, detail="Можно приостановить только активную подписку")
    
    subscription.status = "paused"
    db.commit()
    return {"message": "Подписка приостановлена", "subscription": subscription}

@app.put("/subscriptions/{subscription_id}/resume")
def resume_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    if subscription.status != "paused":
        raise HTTPException(status_code=400, detail="Можно возобновить только приостановленную подписку")
    
    subscription.status = "active"
    db.commit()
    return {"message": "Подписка возобновлена", "subscription": subscription}

# ========== 12. ЗАПУСК ==========
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)