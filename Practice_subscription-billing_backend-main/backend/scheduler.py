from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from database import SessionLocal
from models import Subscription, Payment, Tariff
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_dunning():
    """Обработка неудачных платежей (Dunning)"""
    db = SessionLocal()
    now = datetime.utcnow()
    
    # Находим подписки в статусе payment_error с истекшей датой повторной попытки
    subscriptions = db.query(Subscription).filter(
        Subscription.status == "payment_error",
        Subscription.next_retry_date <= now
    ).all()
    
    logger.info(f"Найдено {len(subscriptions)} подписок для повторной попытки")
    
    for sub in subscriptions:
        # Получаем тариф
        tariff = db.query(Tariff).filter(Tariff.id == sub.tariff_id).first()
        if not tariff:
            continue
        
        # Проверяем количество попыток
        if sub.retry_count >= 3:
            # Превышен лимит — приостанавливаем подписку
            sub.status = "paused"
            db.commit()
            logger.info(f"Подписка {sub.id} приостановлена (превышен лимит попыток)")
            continue
        
        # Имитация списания
        success = simulate_payment(sub.id, tariff.price)
        
        if success:
            # Успешно
            sub.status = "active"
            sub.retry_count = 0
            sub.next_billing_date = now + timedelta(days=30 * tariff.period_months)
            sub.next_retry_date = None
            
            # Создаём запись платежа
            payment = Payment(
                subscription_id=sub.id,
                amount=tariff.price,
                status="paid",
                tariff_name=tariff.name,
                description="Повторная попытка списания"
            )
            db.add(payment)
            db.commit()
            logger.info(f"Подписка {sub.id} возобновлена после повторной попытки")
        else:
            # Неуспешно
            sub.retry_count += 1
            sub.next_retry_date = now + timedelta(days=1)
            
            # Создаём запись платежа
            payment = Payment(
                subscription_id=sub.id,
                amount=tariff.price,
                status="failed",
                tariff_name=tariff.name,
                description=f"Неудачная попытка #{sub.retry_count}"
            )
            db.add(payment)
            db.commit()
            logger.info(f"Подписка {sub.id}: попытка #{sub.retry_count} не удалась")
    
    db.close()

def simulate_payment(subscription_id: int, amount: float) -> bool:
    """Имитация списания (успешно в 70% случаев)"""
    import random
    # Для теста — 70% успеха, 30% ошибка
    return random.random() < 0.7

# Создаём планировщик
scheduler = BackgroundScheduler()
scheduler.add_job(process_dunning, 'interval', minutes=1)  # Каждую минуту для теста
scheduler.start()

logger.info("Планировщик Dunning запущен!")