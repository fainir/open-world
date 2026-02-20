// ══════════════════════════════════════════
// AUTH MODULE
// ══════════════════════════════════════════

const Auth = (() => {
  const TOKEN_KEY = 'ow_token';
  const USER_KEY = 'ow_user';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  }

  function setAuth(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  function authHeaders() {
    const token = getToken();
    if (!token) return {};
    return { 'Authorization': `Bearer ${token}` };
  }

  async function signup(email, username, password) {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Signup failed');
    setAuth(data.access_token, data.user);
    return data.user;
  }

  async function login(login, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    setAuth(data.access_token, data.user);
    return data.user;
  }

  function logout() {
    clearAuth();
  }

  return { getToken, getUser, setAuth, clearAuth, isLoggedIn, authHeaders, signup, login, logout };
})();
