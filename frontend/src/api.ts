import { useSession } from "./store";

let refreshPromise: Promise<boolean> | null = null;
export async function restoreSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) return false;
      const data = await response.json();
      useSession.getState().setSession(data.access_token, data.user);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = useSession.getState().token;
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (
    response.status === 401 &&
    retry &&
    !path.startsWith("/auth/") &&
    (await restoreSession())
  )
    return api(path, options, false);
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      useSession.getState().clear();
    throw new Error(
      data.error?.message ||
        (Array.isArray(data.detail)
          ? data.detail.map((e: { msg: string }) => e.msg).join("; ")
          : data.detail) ||
        "The request could not be completed.",
    );
  }
  return data as T;
}
export function post<T>(
  path: string,
  body: unknown = {},
  idempotent = false,
): Promise<T> {
  return api<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: idempotent
      ? { "Idempotency-Key": crypto.randomUUID() }
      : undefined,
  });
}
export const money = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
