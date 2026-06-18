-- ============================================
-- 1. СОЗДАНИЕ ТИПОВ ENUM
-- ============================================

CREATE TYPE subscription_status AS ENUM (
    'trial', 'active', 'paused', 'cancelled', 'payment_error', 'expired'
);

CREATE TYPE payment_status AS ENUM (
    'pending', 'paid', 'failed', 'prorated'
);

-- ============================================
-- 2. ТАБЛИЦЫ
-- ============================================

-- Пользователи
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Тарифы
CREATE TABLE tariffs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    period_months INT NOT NULL DEFAULT 1,
    trial_days INT NOT NULL DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Подписки
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    tariff_id INT REFERENCES tariffs(id),
    status subscription_status NOT NULL DEFAULT 'trial',
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trial_end_date TIMESTAMP,
    next_billing_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    retry_count INT DEFAULT 0,
    next_retry_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Платежи
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    subscription_id INT REFERENCES subscriptions(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    status payment_status NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tariff_name VARCHAR(100),
    description TEXT
);

-- ============================================
-- 3. ТЕСТОВЫЕ ДАННЫЕ
-- ============================================

-- Админ (пароль: admin123)
INSERT INTO users (email, hashed_password, is_admin) VALUES (
    'admin@billing.local',
    '$2b$12$Gt7lKpXx5xQxQxQxQxQxQx.xQxQxQxQxQxQxQxQxQxQxQxQxQxQxQxQ',
    TRUE
);

-- Базовые тарифы
INSERT INTO tariffs (name, price, period_months, trial_days) VALUES
('Старт', 490.00, 1, 0),
('Бизнес', 1490.00, 1, 14);