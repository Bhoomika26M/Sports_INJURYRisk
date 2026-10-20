// Thin fetch wrapper: base URL, JWT header, JSON errors, file downloads.
const BASE = (import.meta.env.VITE_API_URL || "") + "/api/v1";

export const getToken = () => localStorage.getItem("token");
export const setToken = (t) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token"));

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, { method, headers, body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) });
  if (res.status === 401 && token) {
    setToken(null);
    window.location.assign("/login");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : data.detail?.message
        ? `${data.detail.message}: ${(data.detail.errors || []).join("; ")}`
        : JSON.stringify(data.detail);
    } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: "POST", body }),
  patch: (p, body) => request(p, { method: "PATCH", body }),
  del: (p) => request(p, { method: "DELETE" }),
  upload: (p, form) => request(p, { method: "POST", form }),
  async blobUrl(p) {
    const res = await fetch(BASE + p, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!res.ok) throw new Error("Could not load the video");
    return URL.createObjectURL(await res.blob());
  },
  async download(p, filename) {
    const res = await fetch(BASE + p, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!res.ok) throw new Error("Download failed");
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    a.click();
    URL.revokeObjectURL(url);
  },
};
