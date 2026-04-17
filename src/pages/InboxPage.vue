<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { apiFetch } from '@/lib/api'

type Conversation = {
  id: string
  platform: string
  external_conversation_id: string
  status: 'auto' | 'needs_human' | 'human'
  updated_at: string
}

type Message = {
  id: string
  direction: 'inbound' | 'outbound'
  sender_id?: string | null
  payload: any
  created_at: string
}

type Product = { id: string; title: string; external_url: string }

const loading = ref(true)
const error = ref<string | null>(null)
const conversations = ref<Conversation[]>([])
const selectedId = ref<string | null>(null)
const selected = ref<Conversation | null>(null)
const messages = ref<Message[]>([])

const sending = ref(false)
const input = ref('')

const prodQuery = ref('')
const prodLoading = ref(false)
const prodResults = ref<Product[]>([])

const hasSelection = computed(() => Boolean(selectedId.value))

async function loadConversations() {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch<{ items: Conversation[]; total: number }>(
      '/api/conversations?page=1&page_size=50',
    )
    conversations.value = res.items
    if (!selectedId.value && res.items[0]) {
      selectedId.value = res.items[0].id
      await loadConversation(res.items[0].id)
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadConversation(id: string) {
  selectedId.value = id
  error.value = null
  try {
    const res = await apiFetch<{ conversation: Conversation; messages: Message[] }>(
      `/api/conversations/${id}`,
    )
    selected.value = res.conversation
    messages.value = res.messages
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  }
}

async function sendText() {
  if (!selected.value) return
  const text = input.value.trim()
  if (!text) return
  sending.value = true
  error.value = null
  try {
    await apiFetch(`/api/conversations/${selected.value.id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ type: 'text', text }),
    })
    input.value = ''
    await loadConversation(selected.value.id)
    await loadConversations()
  } catch (e: any) {
    error.value = e?.message || '发送失败'
  } finally {
    sending.value = false
  }
}

async function searchProducts() {
  prodLoading.value = true
  try {
    const res = await apiFetch<{ items: Product[]; total: number }>(
      `/api/products?query=${encodeURIComponent(prodQuery.value)}&page=1&page_size=10`,
    )
    prodResults.value = res.items
  } finally {
    prodLoading.value = false
  }
}

async function sendProduct(pid: string) {
  if (!selected.value) return
  sending.value = true
  error.value = null
  try {
    await apiFetch(`/api/conversations/${selected.value.id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ type: 'products', product_ids: [pid] }),
    })
    await loadConversation(selected.value.id)
    await loadConversations()
  } catch (e: any) {
    error.value = e?.message || '发送失败'
  } finally {
    sending.value = false
  }
}

onMounted(loadConversations)
</script>

<template>
  <AppShell>
    <div class="space-y-4">
      <div class="flex items-end justify-between gap-4">
        <div>
          <div class="text-xl font-semibold">收件箱</div>
          <div class="mt-1 text-sm text-zinc-400">自动处理失败或需要接管时，在这里手动回复</div>
        </div>
        <button
          class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="loadConversations"
        >
          刷新
        </button>
      </div>

      <div v-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
        {{ error }}
      </div>

      <div class="grid gap-4 md:grid-cols-12">
        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 md:col-span-4">
          <div class="border-b border-zinc-800 px-4 py-3 text-xs text-zinc-400">会话</div>
          <div v-if="loading" class="p-4 text-sm text-zinc-400">加载中…</div>
          <div v-else>
            <button
              v-for="c in conversations"
              :key="c.id"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition hover:bg-zinc-900/40"
              :class="selectedId === c.id ? 'bg-zinc-900/50' : ''"
              type="button"
              @click="loadConversation(c.id)"
            >
              <div class="min-w-0">
                <div class="truncate font-medium">{{ c.platform }} · {{ c.external_conversation_id }}</div>
                <div class="mt-1 text-xs text-zinc-400">{{ c.updated_at }}</div>
              </div>
              <span
                class="shrink-0 rounded-full border px-2 py-0.5 text-xs"
                :class="
                  c.status === 'needs_human'
                    ? 'border-amber-500/30 bg-amber-500/10 text-amber-200'
                    : c.status === 'human'
                      ? 'border-sky-500/30 bg-sky-500/10 text-sky-200'
                      : 'border-zinc-700 bg-zinc-900 text-zinc-300'
                "
              >
                {{ c.status }}
              </span>
            </button>
            <div v-if="conversations.length === 0" class="p-4 text-sm text-zinc-400">暂无会话</div>
          </div>
        </div>

        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 md:col-span-8">
          <div class="border-b border-zinc-800 px-4 py-3 text-xs text-zinc-400">
            {{ hasSelection ? '会话详情' : '请选择一个会话' }}
          </div>

          <div v-if="hasSelection" class="p-4">
            <div class="space-y-3">
              <div
                v-for="m in messages"
                :key="m.id"
                class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-3"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="text-xs text-zinc-400">
                    {{ m.direction === 'inbound' ? '客户' : '我方' }} · {{ m.created_at }}
                  </div>
                  <div class="text-xs text-zinc-500">{{ m.sender_id || '' }}</div>
                </div>
                <div class="mt-2 whitespace-pre-wrap text-sm">
                  <template v-if="m.payload?.type === 'text'">
                    {{ m.payload.text }}
                  </template>
                  <template v-else-if="m.payload?.type === 'products'">
                    <div>{{ m.payload.text }}</div>
                    <div class="mt-2 text-xs text-zinc-400">
                      商品ID：{{ (m.payload.product_ids || []).join(', ') }}
                    </div>
                  </template>
                  <template v-else>
                    {{ m.payload }}
                  </template>
                </div>
              </div>
            </div>

            <div class="mt-4 grid gap-3 md:grid-cols-12">
              <div class="md:col-span-8">
                <input
                  v-model="input"
                  class="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                  placeholder="输入文本回复…"
                  @keydown.enter="sendText"
                />
              </div>
              <div class="md:col-span-4">
                <button
                  class="w-full rounded-xl bg-lime-400 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-lime-300 disabled:opacity-60"
                  type="button"
                  :disabled="sending"
                  @click="sendText"
                >
                  {{ sending ? '发送中…' : '发送文本' }}
                </button>
              </div>
            </div>

            <div class="mt-5 rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div class="text-sm font-semibold">手动发商品</div>
              <div class="mt-3 flex flex-wrap items-center gap-2">
                <input
                  v-model="prodQuery"
                  class="w-full max-w-[420px] rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                  placeholder="搜索商品…"
                  @keydown.enter="searchProducts"
                />
                <button
                  class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
                  type="button"
                  @click="searchProducts"
                >
                  {{ prodLoading ? '搜索中…' : '搜索' }}
                </button>
              </div>
              <div class="mt-3 space-y-2">
                <div
                  v-for="p in prodResults"
                  :key="p.id"
                  class="flex items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2"
                >
                  <div class="min-w-0">
                    <div class="truncate text-sm">{{ p.title }}</div>
                    <div class="truncate text-xs text-zinc-400">{{ p.external_url }}</div>
                  </div>
                  <button
                    class="shrink-0 rounded-lg bg-lime-400 px-3 py-1 text-xs font-semibold text-zinc-950 transition hover:bg-lime-300 disabled:opacity-60"
                    type="button"
                    :disabled="sending"
                    @click="sendProduct(p.id)"
                  >
                    发送
                  </button>
                </div>
                <div v-if="prodResults.length === 0" class="text-sm text-zinc-400">暂无结果</div>
              </div>
            </div>
          </div>

          <div v-else class="p-4 text-sm text-zinc-400">左侧选择一个会话</div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

