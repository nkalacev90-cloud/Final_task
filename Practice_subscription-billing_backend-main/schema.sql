-- 1. Создаем специальные типы данных (перечисления) для статусов
CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'paused', 'cancelled', 'payment_error', 'expired');
CREATE TYPE payment_status AS ENUM ('paid', 'failed', 'pending', 'prorated');

-- 2. Таблица пользователей (минимальный набор для биллинга)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Таблица тарифных планов (Старт, Бизнес и т.д.)
CREATE TABLE tariffs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    period_months INT NOT NULL DEFAULT 1,
    trial_days INT NOT NULL DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Таблица подписок пользователей
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

-- 5. Таблица истории платежей
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    subscription_id INT REFERENCES subscriptions(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    status payment_status NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tariff_name VARCHAR(100),
    description TEXT
);

-- 6. Таблица истории изменений подписок (аудит)
CREATE TABLE subscription_history (
    id SERIAL PRIMARY KEY,
    subscription_id INT REFERENCES subscriptions(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_tariff_id INT,
    new_tariff_id INT,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаём админа с паролем "admin123"
-- Хеш пароля: $2b$12$Gt7lKpXx5xQxQxQxQxQxQ.xQxQxQxQxQxQxQxQxQxQxQxQxQxQxQxQ
INSERT INTO users (email, hashed_password, is_admin) VALUES (
    'admin@billing.local',
    '$2b$12$Gt7lKpXx5xQxQxQxQxQxQ.xQxQxQxQxQxQxQxQxQxQxQxQxQxQxQxQ',
    TRUE
);
