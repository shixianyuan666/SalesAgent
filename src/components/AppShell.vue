<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Home, Inbox, Package, Settings, Brain, LogOut } from 'lucide-vue-next'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const router = useRouter()
const { logout } = useAuth()

const items = [
  { to: '/dashboard', label: '概览', icon: Home },
  { to: '/products', label: '商品', icon: Package },
  { to: '/inbox', label: '收件箱', icon: Inbox },
  { to: '/memory', label: '记忆', icon: Brain },
  { to: '/settings', label: '设置', icon: Settings },
]

const active = computed(() => String(route.path || ''))

function onLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div
    class="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-lime-300/20 selection:text-lime-200"
  >
    <div class="mx-auto flex w-full max-w-[1200px] gap-6 px-4 py-6">
      <aside
        class="hidden w-[220px] shrink-0 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4 md:block"
      >
        <div class="flex items-center justify-between gap-3">
          <div class="text-sm font-semibold tracking-wide">智能售卖台</div>
        </div>

        <nav class="mt-5 space-y-1">
          <RouterLink
            v-for="it in items"
            :key="it.to"
            :to="it.to"
            class="group flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
            :class="active === it.to ? 'bg-zinc-900 text-zinc-100' : ''"
          >
            <component :is="it.icon" class="h-4 w-4 text-zinc-400 group-hover:text-zinc-200" />
            <span>{{ it.label }}</span>
          </RouterLink>
        </nav>

        <button
          class="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="onLogout"
        >
          <LogOut class="h-4 w-4" />
          退出
        </button>
      </aside>

      <main class="min-w-0 flex-1">
        <slot />
      </main>
    </div>
  </div>
</template>

