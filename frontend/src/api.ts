import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  async init() {
    this.token = await AsyncStorage.getItem('auth_token');
  }

  setToken(token: string) {
    this.token = token;
    AsyncStorage.setItem('auth_token', token);
  }

  async clearToken() {
    this.token = null;
    await AsyncStorage.removeItem('auth_token');
  }

  private headers() {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  async get(path: string) {
    const res = await fetch(`${API_BASE}/api${path}`, { headers: this.headers() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }

  async post(path: string, body?: any) {
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'POST',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || 'Request failed');
    }
    return res.json();
  }
}

export const api = new ApiClient();
export default api;
