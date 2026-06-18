from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # <-- НОВОЕ ПОЛЕ
    is_admin = Column(Boolean, default=False)         # <-- НОВОЕ ПОЛЕ
    created_at = Column(DateTime, default=datetime.utcnow)

class Tariff(Base):
    __tablename__ = "tariffs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    period_months = Column(Integer, default=1)
    trial_days = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tariff_id = Column(Integer, ForeignKey("tariffs.id"))
    status = Column(String, default="active")
    start_date = Column(DateTime, default=datetime.utcnow)
    next_billing_date = Column(DateTime)
    trial_end_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    retry_count = Column(Integer, default=0)
    next_retry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    payment_date = Column(DateTime, default=datetime.utcnow)
    tariff_name = Column(String, nullable=True)
    description = Column(String, nullable=True)

class TrialUsage(Base):
    __tablename__ = "trial_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tariff_id = Column(Integer, ForeignKey("tariffs.id"))
    used_at = Column(DateTime, default=datetime.utcnow)