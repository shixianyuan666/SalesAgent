<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { apiFetch } from '@/lib/api'

const loading = ref(true)
const error = ref<string | null>(null)
const productsTotal = ref(0)
const conversationsTotal = ref(0)

async function load() {
  loading.value = true
  error.value = null
  try {
    const products = await apiFetch<{ total: number }>('/api/products?page=1&page_size=1')
    const conversations = await apiFetch<{ total: number }>(
      '/api/conversations?page=1&page_size=1',
    )
    productsTotal.value = products.total
    conversationsTotal.value = conversations.total
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="space-y-4">
      <div class="flex items-end justify-between gap-4">
        <div>
          <div class="text-xl font-semibold">概览</div>
          <div class="mt-1 text-sm text-zinc-400">先把闭环跑通：商品→检索→回发→收件箱接管</div>
        </div>
        <button
          class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="load"
        >
          刷新
        </button>
      </div>

      <div v-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
        {{ error }}
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
          <div class="text-xs text-zinc-400">商品总数</div>
          <div class="mt-2 text-3xl font-semibold">
            {{ loading ? '—' : productsTotal }}
          </div>
        </div>
        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
          <div class="text-xs text-zinc-400">会话总数</div>
          <div class="mt-2 text-3xl font-semibold">
            {{ loading ? '—' : conversationsTotal }}
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

