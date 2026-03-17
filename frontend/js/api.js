/**
 * API クライアント
 */
const API_BASE = window.location.origin + "/api";

const Api = {
  _token: null,

  setToken(token) {
    this._token = token;
    localStorage.setItem("auth_token", token);
  },

  getToken() {
    if (!this._token) {
      this._token = localStorage.getItem("auth_token");
    }
    return this._token;
  },

  clearToken() {
    this._token = null;
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
  },

  async _fetch(path, options = {}) {
    const token = this.getToken();
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
      this.clearToken();
      window.App?.showLogin();
      throw new Error("認証が必要です");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
  },

  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "ログインに失敗しました");
    }
    const data = await res.json();
    this.setToken(data.access_token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));
    return data;
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem("auth_user"));
    } catch {
      return null;
    }
  },

  getTantos() {
    return this._fetch("/tantos");
  },

  getShipments(params = {}) {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); });
    return this._fetch(`/shipments?${q.toString()}`);
  },

  getShipment(denno) {
    return this._fetch(`/shipments/${denno}`);
  },

  updateStatus(denno, status, memo = "") {
    const user = this.getUser();
    return this._fetch(`/shipments/${denno}/status`, {
      method: "PUT",
      body: JSON.stringify({ status, memo, updated_by: user?.display_name }),
    });
  },

  scanBarcode(barcode) {
    return this._fetch(`/scan/${encodeURIComponent(barcode)}`);
  },

  sync() {
    return this._fetch("/sync", { method: "POST" });
  },

  getSyncStatus() {
    return this._fetch("/sync/status");
  },

  getSyncLogs() {
    return this._fetch("/sync/logs");
  },

  getLabelUrl(denno) {
    return `${API_BASE}/shipments/${denno}/label?token=${this.getToken()}`;
  },

  getMeisai(denno) {
    const token = this.getToken();
    return fetch(`${API_BASE}/shipments/${denno}/meisai`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((res) => {
      if (!res.ok) throw new Error("明細PDF生成に失敗しました");
      return res.blob();
    });
  },

  health() {
    return this._fetch("/health");
  },
};
