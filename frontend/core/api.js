const BASE = '/api/v1';

function getToken() {
    return sessionStorage.getItem('rsu_token');
}

async function request(endpoint, options = {}) {
    const token = getToken();
    const res = await fetch(BASE + endpoint, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers,
        },
    });

    if (res.status === 401) {
        sessionStorage.removeItem('rsu_token');
        location.href = '/login';
        return;
    }

    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
}

export const api = {
    get:  (endpoint)       => request(endpoint),
    post: (endpoint, body) => request(endpoint, { method: 'POST', body: JSON.stringify(body) }),
};
