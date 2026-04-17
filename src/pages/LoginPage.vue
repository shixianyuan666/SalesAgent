<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { login } = useAuth()

const username = ref('admin')
const password = ref('admin')
const error = ref<string | null>(null)
const loading = ref(false)

async function onSubmit() {
  error.value = null
  loading.value = true
  try {
    await login(username.value, password.value)
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e?.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100">
    <div class="mx-auto flex max-w-[520px] flex-col px-4 py-16">
      <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-8">
        <div class="text-lg font-semibold">登录</div>
        <div class="mt-2 text-sm text-zinc-400">默认账号：admin / admin</div>

        <form class="mt-6 space-y-4" @submit.prevent="onSubmit">
          <div>
            <div class="text-xs text-zinc-400">用户名</div>
            <input
              v-model="username"
              class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              autocomplete="username"
            />
          </div>

          <div>
            <div class="text-xs text-zinc-400">密码</div>
            <input
              v-model="password"
              type="password"
              class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              autocomplete="current-password"
            />
          </div>

          <div v-if="error" class="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm">
            {{ error }}
          </div>

          <button
            class="w-full rounded-xl bg-lime-400 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-lime-300 disabled:opacity-60"
            type="submit"
            :disabled="loading"
          >
            {{ loading ? '登录中…' : '进入控制台' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

