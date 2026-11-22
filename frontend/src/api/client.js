import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const useMock = import.meta.env.VITE_USE_MOCK === 'true';

// Simple mock data store
const mockData = {
  '/auth/send-otp': { status: 200, data: { message: 'OTP sent (mock)' } },
  '/auth/verify-otp': {
    status: 200,
    data: {
      message: 'Logged in (mock)',
      session: { access_token: 'mock-access', refresh_token: 'mock-refresh' },
      profile: { id: 'user-1', full_name: 'Demo Receiver', role: 'receiver', approval_status: 'pending', is_verified: false }
    }
  },
  '/listings/': {
    status: 200,
    data: {
      listings: Array.from({ length: 10 }, (_, i) => ({
        id: `listing-${i}`,
        title: `Food ${i}`,
        food_category: i % 2 === 0 ? 'human' : 'animal',
        quantity: `${i+1} kg`,
        servings: (i+1) * 5,
        approx_latitude: 12.97 + i * 0.01,
        approx_longitude: 77.59 + i * 0.01,
        distance_km: Math.round(Math.random() * 20),
        expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        safe_until: new Date(Date.now() + 60 * 60 * 1000).toISOString()
      }))
    }
  },
  // detail endpoint returns maybe address only if claim active – mock always without exact address
  '/listings/listing-0': { status: 200, data: { listing: { id: 'listing-0', title: 'Food 0', description: 'Demo', food_category: 'human', quantity: '1 kg', servings: 5, approx_latitude: 12.97, approx_longitude: 77.59, distance_km: 5, expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString() } } },
  '/claims/create': { status: 200, data: { claim: { id: 'claim-123', expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString() } } },
  '/claims/my': { status: 200, data: { claims: [] } },
  '/claims/claim-123/confirm-pickup': { status: 200, data: { message: 'Pickup confirmed (mock)' } },
  '/impact/summary': { status: 200, data: { is_demo: true, generated_at: new Date().toISOString(), completed_pickups: 0, meals_rescued: 0, servings_unknown_count: 0, distinct_donors: 0, distinct_receiver_orgs: 0, category_breakdown: { human: 0, animal: 0 }, last_30_days: [] } }
};

function getMockResponse(url, config) {
  // Simple matching ignoring query params
  const path = url.replace(baseURL, '').split('?')[0];
  const entry = mockData[path];
  if (!entry) {
    return Promise.reject({ response: { status: 404, data: { error: { code: 'not_found', message: 'Mock not found' } } } });
  }
  // Simulate latency
  return new Promise((resolve) => setTimeout(() => resolve({ status: entry.status, data: entry.data, headers: { date: new Date().toUTCString() } }), 50));
}

const instance = axios.create({ baseURL, timeout: 8000 });

// Request interceptor for auth header & request‑id capture
instance.interceptors.request.use((config) => {
  const access = sessionStorage.getItem('access_token');
  if (access) config.headers.Authorization = `Bearer ${access}`;
  config.headers['X-Request-ID'] = crypto.randomUUID();
  return config;
});

// Response interceptor – normalise error shapes & handle 401
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const resp = error.response || {};
    const status = resp.status;
    if (status === 401) {
      // clear session and redirect to login (handled by caller)
    }
    // Normalise error shape
    const data = resp.data || {};
    const norm = data.error ? data.error : { code: data.detail || 'error', message: data.detail || 'Error', request_id: data.request_id || '' };
    return Promise.reject({ response: { status, data: { error: norm } } });
  }
);

// Export a wrapper that decides between mock and real
const client = {
  get: (url, config) => (useMock ? getMockResponse(url, config) : instance.get(url, config)),
  post: (url, data, config) => (useMock ? getMockResponse(url, config).then(r => r) : instance.post(url, data, config)),
  put: (url, data, config) => (useMock ? getMockResponse(url, config) : instance.put(url, data, config)),
  delete: (url, config) => (useMock ? getMockResponse(url, config) : instance.delete(url, config))
};

export default client;
