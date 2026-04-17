import { computed, ref } from 'vue'
import { apiFetch, setToken } from '@/lib/api'

const tokenRef = ref<string | null>(localStorage.getItem('auth_token'))

export function useAuth() {
  const isAuthed = computed(() => Boolean(tokenRef.value))

  async function login(username: string, password: string) {
    const res = await apiFetch<{ token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    tokenRef.value = res.token
    setToken(res.token)
  }

  function logout() {
    tokenRef.value = null
    setToken(null)
  }

  return { token: tokenRef, isAuthed, login, logout }
}

