<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { apiFetch } from '@/lib/api'

const error = ref<string | null>(null)
const loading = ref(true)
const saving = ref(false)

const feishuEnabled = ref(true)
const feishuBaseUrl = ref('https://open.feishu.cn')
const feishuAccessToken = ref('')
const feishuAppId = ref('')
const feishuAppSecret = ref('')
const feishuVerifyToken = ref('')

const llmBaseUrl = ref('')
const llmApiKey = ref('')
const llmChatModel = ref('')
const llmEmbeddingModel = ref('')

const topN = ref(3)
const minScore = ref(0.35)
const fallbackText = ref('我暂时没找到完全匹配的商品。你可以补充一下用途/预算/规格吗？')

async function load() {
  loading.value = true
  error.value = null
  try {
    const connectors = await apiFetch<{ connectors: any }>('/api/settings/connectors')
    const feishu = connectors.connectors?.feishu || {}
    feishuEnabled.value = feishu.enabled ?? true
    feishuBaseUrl.value = feishu.base_url || 'https://open.feishu.cn'
    feishuAccessToken.value = ''
    feishuAppId.value = feishu.app_id || ''
    feishuAppSecret.value = ''
    feishuVerifyToken.value = feishu.verify_token || ''

    const llm = await apiFetch<{ llm: any }>('/api/settings/llm')
    llmBaseUrl.value = llm.llm?.base_url || ''
    llmApiKey.value = ''
    llmChatModel.value = llm.llm?.chat_model || ''
    llmEmbeddingModel.value = llm.llm?.embedding_model || ''

    const agent = await apiFetch<{ agent: any }>('/api/settings/agent')
    topN.value = agent.agent?.top_n ?? 3
    minScore.value = agent.agent?.min_relevance_score ?? 0.35
    fallbackText.value = agent.agent?.fallback_text || fallbackText.value
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function saveAll() {
  saving.value = true
  error.value = null
  try {
    await apiFetch('/api/settings/connectors', {
      method: 'PUT',
      body: JSON.stringify({
        feishu: {
          enabled: feishuEnabled.value,
          base_url: feishuBaseUrl.value,
          access_token: feishuAccessToken.value || undefined,
          app_id: feishuAppId.value || undefined,
          app_secret: feishuAppSecret.value || undefined,
          verify_token: feishuVerifyToken.value || undefined,
        },
      }),
    })

    await apiFetch('/api/settings/llm', {
      method: 'PUT',
      body: JSON.stringify({
        base_url: llmBaseUrl.value,
        api_key: llmApiKey.value || undefined,
        chat_model: llmChatModel.value,
        embedding_model: llmEmbeddingModel.value,
      }),
    })

    await apiFetch('/api/settings/agent', {
      method: 'PUT',
      body: JSON.stringify({
        top_n: topN.value,
        min_relevance_score: minScore.value,
        fallback_text: fallbackText.value,
      }),
    })

    await load()
  } catch (e: any) {
    error.value = e?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="space-y-4">
      <div class="flex items-end justify-between gap-4">
        <div>
          <div class="text-xl font-semibold">设置</div>
          <div class="mt-1 text-sm text-zinc-400">飞书连接器、模型与智能体策略</div>
        </div>
        <button
          class="rounded-xl bg-lime-400 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-lime-300 disabled:opacity-60"
          type="button"
          :disabled="saving"
          @click="saveAll"
        >
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>

      <div v-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
        {{ error }}
      </div>

      <div v-if="loading" class="text-sm text-zinc-400">加载中…</div>

      <div v-else class="grid gap-4 md:grid-cols-2">
        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
          <div class="text-sm font-semibold">飞书</div>
          <div class="mt-4 space-y-3">
            <label class="flex items-center gap-2 text-sm text-zinc-300">
              <input v-model="feishuEnabled" type="checkbox" class="accent-lime-400" />
              启用飞书连接器
            </label>
            <div>
              <div class="text-xs text-zinc-400">Base URL</div>
              <input
                v-model="feishuBaseUrl"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">Access Token</div>
              <input
                v-model="feishuAccessToken"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="tenant_access_token 或 bot token"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">App ID</div>
              <input
                v-model="feishuAppId"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="留空则不修改"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">App Secret</div>
              <input
                v-model="feishuAppSecret"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="留空则不修改"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">Verify Token（Webhook）</div>
              <input
                v-model="feishuVerifyToken"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="事件订阅回调Token（可选，推荐配置）"
              />
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5">
          <div class="text-sm font-semibold">LLM / Embedding（接口模式）</div>
          <div class="mt-4 space-y-3">
            <div>
              <div class="text-xs text-zinc-400">Base URL（OpenAI兼容）</div>
              <input
                v-model="llmBaseUrl"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="例如 https://api.xxx.com"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">API Key</div>
              <input
                v-model="llmApiKey"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
                placeholder="仅在保存时写入"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">Chat Model</div>
              <input
                v-model="llmChatModel"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">Embedding Model</div>
              <input
                v-model="llmEmbeddingModel"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div class="text-xs text-zinc-500">
              未配置模型时，系统会使用“可重复的文本哈希向量”先把流程跑通；配置后自动切换真实向量与一致性校验。
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-5 md:col-span-2">
          <div class="text-sm font-semibold">智能体策略（LangGraph）</div>
          <div class="mt-4 grid gap-3 md:grid-cols-3">
            <div>
              <div class="text-xs text-zinc-400">TopN</div>
              <input
                v-model.number="topN"
                type="number"
                min="1"
                max="5"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">最小相关分</div>
              <input
                v-model.number="minScore"
                type="number"
                step="0.01"
                min="0"
                max="1"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
          </div>
          <div class="mt-3">
            <div class="text-xs text-zinc-400">兜底话术（用于澄清）</div>
            <textarea
              v-model="fallbackText"
              rows="3"
              class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
            />
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
