const API_URL = 'http://127.0.0.1:8001';

function getToken() {
    return localStorage.getItem('access_token');
}

function setToken(token) {
    localStorage.setItem('access_token', token);
}

function clearToken() {
    localStorage.removeItem('access_token');
}

function isLoggedIn() {
    return !!getToken();
}

async function apiRequest(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token && !url.includes('/token') && !url.includes('/register')) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${url}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        clearToken();
        window.location.href = 'login.html';
        throw new Error('Сессия истекла');
    }

    return response;
}

async function login(email, password) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка входа');
    }

    const data = await response.json();
    setToken(data.access_token);
    return data;
}

function logout() {
    clearToken();
    window.location.href = 'login.html';
}

async function getCurrentUser() {
    try {
        const response = await apiRequest('/users/me');
        if (!response.ok) return null;
        return await response.json();
    } catch {
        return null;
    }
}

async function getCurrentSubscription() {
    try {
        const response = await apiRequest('/subscriptions/me');
        if (response.status === 404) return null;
        if (!response.ok) throw new Error('Ошибка загрузки подписки');
        return await response.json();
    } catch (error) {
        console.error('getCurrentSubscription error:', error);
        return null;
    }
}

async function createSubscription(tariffId) {
    const response = await apiRequest(`/subscriptions?tariff_id=${tariffId}`, {
        method: 'POST'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка оформления');
    }
    return await response.json();
}

async function cancelSubscription(subscriptionId) {
    const response = await apiRequest(`/subscriptions/${subscriptionId}/cancel`, {
        method: 'PUT'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка отмены');
    }
    return await response.json();
}

async function pauseSubscription(subscriptionId) {
    const response = await apiRequest(`/subscriptions/${subscriptionId}/pause`, {
        method: 'PUT'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка приостановки');
    }
    return await response.json();
}

async function resumeSubscription(subscriptionId) {
    const response = await apiRequest(`/subscriptions/${subscriptionId}/resume`, {
        method: 'PUT'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка возобновления');
    }
    return await response.json();
}

async function changeTariff(subscriptionId, newTariffId) {
    const response = await apiRequest(
        `/subscriptions/${subscriptionId}/change-tariff?new_tariff_id=${newTariffId}`,
        { method: 'PUT' }
    );
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка смены тарифа');
    }
    return await response.json();
}

async function getPayments(subscriptionId, startDate = '', endDate = '') {
    let url = `/payments?subscription_id=${subscriptionId}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    const response = await apiRequest(url);
    if (!response.ok) throw new Error('Ошибка загрузки платежей');
    return await response.json();
}

async function getTariffs() {
    const response = await apiRequest('/tariffs');
    if (!response.ok) throw new Error('Ошибка загрузки тарифов');
    return await response.json();
}

async function adminGetSubscriptions() {
    const response = await apiRequest('/admin/subscriptions');
    if (!response.ok) throw new Error('Ошибка загрузки подписок');
    return await response.json();
}

async function adminGetRevenue(startDate, endDate) {
    const response = await apiRequest(`/admin/revenue?start_date=${startDate}&end_date=${endDate}`);
    if (!response.ok) throw new Error('Ошибка загрузки выручки');
    return await response.json();
}

async function adminPauseSubscription(subscriptionId) {
    const response = await apiRequest(`/admin/subscriptions/${subscriptionId}/pause`, {
        method: 'PUT'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка приостановки');
    }
    return await response.json();
}

async function adminCancelSubscription(subscriptionId) {
    const response = await apiRequest(`/admin/subscriptions/${subscriptionId}/cancel`, {
        method: 'PUT'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Ошибка отмены');
    }
    return await response.json();
}

// ========== ПОЛУЧИТЬ ВСЕ ПОДПИСКИ ПОЛЬЗОВАТЕЛЯ ==========
async function getMySubscriptions() {
    try {
        const response = await apiRequest('/my-subscriptions');
        if (!response.ok) throw new Error('Ошибка загрузки подписок');
        return await response.json();
    } catch (error) {
        console.error('getMySubscriptions error:', error);
        return [];
    }
}

// ========== ПОЛУЧИТЬ ПЛАТЕЖИ ПО ВСЕМ ПОДПИСКАМ ==========
async function getAllMyPayments(startDate = '', endDate = '') {
    try {
        const subscriptions = await getMySubscriptions();
        if (!subscriptions || subscriptions.length === 0) return [];

        // Собираем все платежи по всем подпискам
        let allPayments = [];
        for (const sub of subscriptions) {
            let url = `/payments?subscription_id=${sub.id}`;
            if (startDate) url += `&start_date=${startDate}`;
            if (endDate) url += `&end_date=${endDate}`;
            
            const response = await apiRequest(url);
            if (response.ok) {
                const payments = await response.json();
                allPayments = allPayments.concat(payments);
            }
        }
        
        // Сортируем по дате (сначала свежие)
        allPayments.sort((a, b) => new Date(b.payment_date) - new Date(a.payment_date));
        return allPayments;
    } catch (error) {
        console.error('getAllMyPayments error:', error);
        return [];
    }
}
