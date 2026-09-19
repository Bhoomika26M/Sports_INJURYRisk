const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(status: number, data: any, message: string = "API Error") {
    super(message);
    this.status = status;
    this.data = data;
  }
}

let inMemoryToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

async function refreshTokenSingleFlight(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        inMemoryToken = data.access_token;
        return inMemoryToken;
      } else {
        inMemoryToken = null;
        return null;
      }
    } catch {
      inMemoryToken = null;
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export const apiClient = {
  setToken(token: string | null) {
    inMemoryToken = token;
  },

  getToken(): string | null {
    return inMemoryToken;
  },

  async ensureToken(): Promise<string | null> {
    if (inMemoryToken) {
      return inMemoryToken;
    }
    return await refreshTokenSingleFlight();
  },

  async fetchWithAuth(endpoint: string, options: RequestInit = {}) {
    // If no in-memory token yet and not a public auth route, resolve token first
    if (!inMemoryToken && endpoint !== "/auth/refresh" && endpoint !== "/auth/login" && endpoint !== "/auth/register") {
      await refreshTokenSingleFlight();
    }

    let token = inMemoryToken;

    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    // Include credentials so the backend gets the httpOnly refresh_token cookie
    const config: RequestInit = {
      ...options,
      headers,
      credentials: "include",
    };

    let response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    // If 401, attempt token rotation via single flight
    if (response.status === 401 && endpoint !== "/auth/refresh" && endpoint !== "/auth/login") {
      const newToken = await refreshTokenSingleFlight();
      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
          ...config,
          headers,
        });
      } else {
        if (typeof window !== "undefined") {
          document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
          window.location.href = "/login";
        }
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData, errorData?.detail?.error?.message || "API request failed");
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  },

  async refresh() {
    return await refreshTokenSingleFlight();
  }
};

export async function fetchAsObjectUrl(path: string): Promise<string> {
  const token = await apiClient.ensureToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    credentials: "include"
  });
  if (!res.ok) throw new Error("Failed to fetch object");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
