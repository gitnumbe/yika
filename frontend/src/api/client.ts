/** API 客户端：统一 BASE（开发 8010 / 生产由 VITE_API_BASE 注入） */
const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8010";

export function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("token");
  const isForm = options.body instanceof FormData;
  return fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(token ? { token } : {}),
      ...(options.headers || {}),
    },
  }).then((r) => {
    if (r.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return r.json();
  });
}
