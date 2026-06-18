-- 1. Добавляем базовые тарифы из задания
INSERT INTO tariffs (name, price, period_months, trial_days) VALUES
('Старт', 490.00, 1, 0),
('Бизнес', 1490.00, 1, 14);

-- 2. Добавляем тестовых пользователей
INSERT INTO users (email) VALUES
('user1@example.com'),
('user2@example.com'),
('admin@billing.local');

-- 3. Добавляем тестовые подписки пользователей
-- Пользователь 1 на тарифе Старт (активная подписка)
INSERT INTO subscriptions (user_id, tariff_id, status, start_date, next_billing_date) VALUES
(1, 1, 'active', NOW() - INTERVAL '15 days', NOW() + INTERVAL '15 days');

-- Пользователь 2 на тарифе Бизнес (в процессе пробного периода)
INSERT INTO subscriptions (user_id, tariff_id, status, start_date, next_billing_date, trial_end_date) VALUES
(2, 2, 'trial', NOW() - INTERVAL '5 days', NOW() + INTERVAL '9 days', NOW() + INTERVAL '9 days');

-- 4. Добавляем историю платежей для симуляции финансовой активности
-- Успешный платеж от Пользователя 1 за тариф Старт
INSERT INTO payments (subscription_id, amount, status, payment_date, tariff_name) VALUES
(1, 490.00, 'paid', NOW() - INTERVAL '15 days', 'Старт');

-- Неудачная попытка списания (для проверки механики Dunning-процесса)
INSERT INTO payments (subscription_id, amount, status, payment_date, tariff_name, description) VALUES
(1, 490.00, 'failed', NOW(), 'Старт', 'Недостаточно средств');
