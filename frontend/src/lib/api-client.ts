import { hasSessionHint, setSessionHint } from "@/lib/session";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Every failed API call surfaces as an ApiError with a message safe to show a person. */
export class ApiError extends Error {
  status: number;
  code: string | null;
  data: unknown;

  constructor(status: number, message: string, code: string | null = null, data: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

const NETWORK_MESSAGE = "We couldn't reach the server. Check your connection and try again.";

function extractError(status: number, body: unknown): ApiError {
  const b = (body ?? {}) as { detail?: unknown };
  const detail = b.detail as
    | { error?: { code?: string; message?: string } }
    | Array<{ msg?: string; message?: string }>
    | string
    | undefined;

  let message: string | undefined;
  let code: string | null = null;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    message = detail.error?.message;
    code = detail.error?.code ?? null;
  } else if (Array.isArray(detail)) {
    message = detail.map((d) => d.msg || d.message).filter(Boolean).join("; ");
  } else if (typeof detail === "string") {
    message = detail;
  }

  if (!message) {
    message =
      status === 401 ? "Your session has ended. Please sign in again."
      : status === 403 ? "You don't have permission to do that."
      : status === 404 ? "We couldn't find what you were looking for."
      : status >= 500 ? "Something went wrong on our side. Please try again in a moment."
      : "That didn't work. Please try again.";
  }
  return new ApiError(status, message, code, body);
}

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;
let onSessionExpired: (() => void) | null = null;

async function refreshSingleFlight(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", credentials: "include" });
      if (!res.ok) {
        accessToken = null;
        return null;
      }
      const data = (await res.json()) as { access_token: string };
      accessToken = data.access_token;
      setSessionHint(true); // the backend rotates the cookie (7d) — keep the hint in step
      return accessToken;
    } catch {
      accessToken = null;
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

const AUTH_PATHS = new Set(["/auth/refresh", "/auth/login", "/auth/register", "/auth/logout"]);

function expireSession() {
  setSessionHint(false);
  onSessionExpired?.();
}

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const isAuthPath = AUTH_PATHS.has(path);
  if (!accessToken && !isAuthPath) await refreshSingleFlight();

  const send = (token: string | null) => {
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" });
  };

  let res: Response;
  try {
    res = await send(accessToken);
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, NETWORK_MESSAGE, "NETWORK");
  }

  if (res.status === 401 && !isAuthPath) {
    const fresh = await refreshSingleFlight();
    if (!fresh) {
      expireSession();
      throw new ApiError(401, "Your session has ended. Please sign in again.", "SESSION_EXPIRED");
    }
    try {
      res = await send(fresh);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") throw e;
      throw new ApiError(0, NETWORK_MESSAGE, "NETWORK");
    }
  }
  return res;
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await authedFetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw extractError(res.status, errBody);
  }
  if (res.status === 204) return null as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, undefined, signal),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  del: <T = null>(path: string) => request<T>("DELETE", path),
};

export const apiClient = {
  setToken(token: string | null) {
    accessToken = token;
  },
  getToken: () => accessToken,
  /** True when it's worth trying to restore a session on page load. */
  canRestoreSession: () => hasSessionHint(),
  refresh: refreshSingleFlight,
  setSessionExpiredHandler(fn: (() => void) | null) {
    onSessionExpired = fn;
  },
};

/** Fetch a protected file (video, image) as a blob URL — `<video src>` can't send auth headers. */
export async function fetchAsObjectUrl(path: string, signal?: AbortSignal): Promise<string> {
  const res = await authedFetch(path, { signal });
  if (!res.ok) throw extractError(res.status, await res.json().catch(() => null));
  return URL.createObjectURL(await res.blob());
}

/** Download a protected file using the signed-in session (plain <a href> links can't). */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await authedFetch(path);
  if (!res.ok) throw extractError(res.status, await res.json().catch(() => null));

  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const filename = match ? decodeURIComponent(match[1]) : fallbackName;

  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export type UploadOptions = {
  onProgress?: (loaded: number, total: number) => void;
  signal?: AbortSignal;
};

/**
 * PUT a file to the (mock) presigned storage URL with progress.
 * The storage endpoint requires the Bearer token, so we send it — and retry once
 * with a refreshed token if the first attempt comes back 401.
 */
export async function uploadFile(url: string, file: File, opts: UploadOptions = {}): Promise<void> {
  const attempt = (token: string | null) =>
    new Promise<{ status: number; body: unknown }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", url);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) opts.onProgress?.(e.loaded, e.total);
      };
      xhr.onload = () => {
        let body: unknown = null;
        try { body = JSON.parse(xhr.responseText); } catch { /* non-JSON body */ }
        resolve({ status: xhr.status, body });
      };
      xhr.onerror = () => reject(new ApiError(0, NETWORK_MESSAGE, "NETWORK"));
      xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
      if (opts.signal) {
        if (opts.signal.aborted) return reject(new DOMException("Upload cancelled", "AbortError"));
        opts.signal.addEventListener("abort", () => xhr.abort(), { once: true });
      }
      xhr.send(file);
    });

  if (!accessToken) await refreshSingleFlight();
  let result = await attempt(accessToken);
  if (result.status === 401) {
    const fresh = await refreshSingleFlight();
    if (!fresh) {
      expireSession();
      throw new ApiError(401, "Your session has ended. Please sign in again.", "SESSION_EXPIRED");
    }
    result = await attempt(fresh);
  }
  if (result.status < 200 || result.status >= 300) throw extractError(result.status, result.body);
}
