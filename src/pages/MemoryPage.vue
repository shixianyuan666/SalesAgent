<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { apiFetch } from '@/lib/api'

type Memory = {
  user_id: string
  preferences: Record<string, any>
  summary_text: string
  updated_at: string
}

const loading = ref(true)
const error = ref<string | null>(null)
const query = ref('')
const items = ref<Memory[]>([])
const selectedId = ref<string | null>(null)
const selected = ref<Memory | null>(null)

const hasSelection = computed(() => Boolean(selectedId.value))

async function loadList() {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch<{ items: Memory[]; total: number }>(
      `/api/memory/users?query=${encodeURIComponent(query.value)}&page=1&page_size=50`,
    )
    items.value = res.items
    if (!selectedId.value && res.items[0]) {
      await loadOne(res.items[0].user_id)
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadOne(userId: string) {
  selectedId.value = userId
  error.value = null
  try {
    const res = await apiFetch<{ memory: Memory }>(`/api/memory/users/${encodeURIComponent(userId)}`)
    selected.value = res.memory
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  }
}

async function clearMemory(userId: string) {
  error.value = null
  try {
    await apiFetch(`/api/memory/users/${encodeURIComponent(userId)}`, { method: 'DELETE' })
    selected.value = null
    selectedId.value = null
    await loadList()
  } catch (e: any) {
    error.value = e?.message || '清除失败'
  }
}

onMounted(loadList)
</script>

<template>
  <AppShell>
    <div class="space-y-4">
      <div class="flex items-end justify-between gap-4">
        <div>
          <div class="text-xl font-semibold">记忆</div>
          <div class="mt-1 text-sm text-zinc-400">永久保存，支持按用户一键清除</div>
        </div>
        <button
          class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="loadList"
        >
          刷新
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="query"
          class="w-full max-w-[420px] rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-lime-400/60"
          placeholder="搜索 user_id / 摘要…"
          @keydown.enter="loadList"
        />
        <button
          class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="loadList"
        >
          搜索
        </button>
      </div>

      <div v-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
        {{ error }}
      </div>

      <div class="grid gap-4 md:grid-cols-12">
        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 md:col-span-4">
          <div class="border-b border-zinc-800 px-4 py-3 text-xs text-zinc-400">用户列表</div>
          <div v-if="loading" class="p-4 text-sm text-zinc-400">加载中…</div>
          <div v-else>
            <button
              v-for="m in items"
              :key="m.user_id"
              class="w-full px-4 py-3 text-left text-sm transition hover:bg-zinc-900/40"
              :class="selectedId === m.user_id ? 'bg-zinc-900/50' : ''"
              type="button"
              @click="loadOne(m.user_id)"
            >
              <div class="truncate font-medium">{{ m.user_id }}</div>
              <div class="mt-1 truncate text-xs text-zinc-400">{{ m.summary_text }}</div>
            </button>
            <div v-if="items.length === 0" class="p-4 text-sm text-zinc-400">暂无数据</div>
          </div>
        </div>

        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 md:col-span-8">
          <div class="border-b border-zinc-800 px-4 py-3 text-xs text-zinc-400">
            {{ hasSelection ? '记忆详情' : '请选择一个用户' }}
          </div>
          <div v-if="hasSelection && selected" class="p-4 space-y-3">
            <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
              <div class="text-xs text-zinc-400">偏好 preferences</div>
              <pre class="mt-2 overflow-auto text-xs text-zinc-200">{{ selected.preferences }}</pre>
            </div>
            <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
              <div class="text-xs text-zinc-400">摘要 summary</div>
              <div class="mt-2 whitespace-pre-wrap text-sm">{{ selected.summary_text }}</div>
            </div>
            <button
              class="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-200 transition hover:bg-red-500/15"
              type="button"
              @click="clearMemory(selected.user_id)"
            >
              清除该用户记忆
            </button>
          </div>
          <div v-else class="p-4 text-sm text-zinc-400">左侧选择一个用户</div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

