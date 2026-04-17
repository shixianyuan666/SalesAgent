export type ApiError = {
  status: number
  message: string
}

function getToken(): string | null {
  return localStorage.getItem('auth_token')
}

export function setToken(token: string | null) {
  if (!token) {
    localStorage.removeItem('auth_token')
    return
  }
  localStorage.setItem('auth_token', token)
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()

  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(path, {
    ...options,
    headers,
  })

  if (res.status === 204) return undefined as T

  let data: any = null
  const text = await res.text()
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!res.ok) {
    const err: ApiError = {
      status: res.status,
      message: (data && (data.detail || data.message)) || '请求失败',
    }
    throw err
  }

  return data as T
}

