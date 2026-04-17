<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { apiFetch } from '@/lib/api'

type ProductImage = { id: string; url: string }
type Product = {
  id: string
  title: string
  sku?: string | null
  description?: string | null
  tags: string[]
  status: 'active' | 'inactive'
  external_url: string
  images: ProductImage[]
  updated_at: string
}

const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<Product[]>([])
const query = ref('')

const editing = ref<Product | null>(null)
const formTitle = ref('')
const formSku = ref('')
const formDesc = ref('')
const formTags = ref('')
const formUrl = ref('')
const formStatus = ref<'active' | 'inactive'>('active')

const uploading = ref(false)
const reindexing = ref(false)

const isOpen = computed(() => Boolean(editing.value))

function openCreate() {
  editing.value = {
    id: '',
    title: '',
    sku: '',
    description: '',
    tags: [],
    status: 'active',
    external_url: '',
    images: [],
    updated_at: '',
  }
  formTitle.value = ''
  formSku.value = ''
  formDesc.value = ''
  formTags.value = ''
  formUrl.value = ''
  formStatus.value = 'active'
}

function openEdit(p: Product) {
  editing.value = p
  formTitle.value = p.title
  formSku.value = p.sku || ''
  formDesc.value = p.description || ''
  formTags.value = (p.tags || []).join(', ')
  formUrl.value = p.external_url || ''
  formStatus.value = p.status
}

function close() {
  editing.value = null
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await apiFetch<{ items: Product[]; total: number }>(
      `/api/products?query=${encodeURIComponent(query.value)}&page=1&page_size=50`,
    )
    items.value = res.items
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!editing.value) return
  error.value = null
  const payload = {
    title: formTitle.value.trim(),
    sku: formSku.value.trim() || undefined,
    description: formDesc.value.trim() || undefined,
    tags: formTags.value
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean),
    status: formStatus.value,
    external_url: formUrl.value.trim(),
  }
  if (!payload.title || !payload.external_url) {
    error.value = '标题和链接必填'
    return
  }

  try {
    if (!editing.value.id) {
      const created = await apiFetch<Product>('/api/products', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      await load()
      const fresh = await apiFetch<Product>(`/api/products/${created.id}`)
      openEdit(fresh)
    } else {
      await apiFetch<Product>(`/api/products/${editing.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      await load()
      const fresh = await apiFetch<Product>(`/api/products/${editing.value.id}`)
      openEdit(fresh)
    }
  } catch (e: any) {
    error.value = e?.message || '保存失败'
  }
}

async function onUploadImages(ev: Event) {
  const input = ev.target as HTMLInputElement
  if (!editing.value?.id) return
  if (!input.files || input.files.length === 0) return
  uploading.value = true
  error.value = null
  try {
    const fd = new FormData()
    for (const f of Array.from(input.files)) fd.append('files', f)
    await apiFetch<{ images: ProductImage[] }>(`/api/products/${editing.value.id}/images`, {
      method: 'POST',
      body: fd,
    })
    const fresh = await apiFetch<Product>(`/api/products/${editing.value.id}`)
    openEdit(fresh)
    await load()
    input.value = ''
  } catch (e: any) {
    error.value = e?.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function deleteImage(imageId: string) {
  if (!editing.value?.id) return
  error.value = null
  try {
    await apiFetch(`/api/products/${editing.value.id}/images/${imageId}`, { method: 'DELETE' })
    const fresh = await apiFetch<Product>(`/api/products/${editing.value.id}`)
    openEdit(fresh)
    await load()
  } catch (e: any) {
    error.value = e?.message || '删除失败'
  }
}

async function reindex() {
  reindexing.value = true
  error.value = null
  try {
    await apiFetch('/api/products/reindex', { method: 'POST' })
  } catch (e: any) {
    error.value = e?.message || '向量重建失败'
  } finally {
    reindexing.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="space-y-4">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div class="text-xl font-semibold">商品</div>
          <div class="mt-1 text-sm text-zinc-400">上传/更新商品后，点击“重建向量”让智能体更准</div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100 disabled:opacity-60"
            type="button"
            :disabled="reindexing"
            @click="reindex"
          >
            {{ reindexing ? '重建中…' : '重建向量' }}
          </button>
          <button
            class="rounded-xl bg-lime-400 px-3 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-lime-300"
            type="button"
            @click="openCreate"
          >
            新建商品
          </button>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <input
          v-model="query"
          class="w-full max-w-[420px] rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-lime-400/60"
          placeholder="搜索标题/描述/标签…"
          @keydown.enter="load"
        />
        <button
          class="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
          type="button"
          @click="load"
        >
          搜索
        </button>
      </div>

      <div v-if="error" class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
        {{ error }}
      </div>

      <div class="rounded-2xl border border-zinc-800 bg-zinc-950/60">
        <div class="grid grid-cols-12 gap-2 border-b border-zinc-800 px-4 py-3 text-xs text-zinc-400">
          <div class="col-span-5">商品</div>
          <div class="col-span-3">标签</div>
          <div class="col-span-2">状态</div>
          <div class="col-span-2 text-right">操作</div>
        </div>
        <div v-if="loading" class="p-4 text-sm text-zinc-400">加载中…</div>
        <div v-else>
          <div
            v-for="p in items"
            :key="p.id"
            class="grid grid-cols-12 items-center gap-2 px-4 py-3 text-sm hover:bg-zinc-900/40"
          >
            <div class="col-span-5 min-w-0">
              <div class="truncate font-medium">{{ p.title }}</div>
              <div class="truncate text-xs text-zinc-400">{{ p.external_url }}</div>
            </div>
            <div class="col-span-3 min-w-0">
              <div class="truncate text-xs text-zinc-400">{{ (p.tags || []).join(', ') }}</div>
            </div>
            <div class="col-span-2">
              <span
                class="inline-flex rounded-full border px-2 py-0.5 text-xs"
                :class="
                  p.status === 'active'
                    ? 'border-lime-500/30 bg-lime-500/10 text-lime-200'
                    : 'border-zinc-700 bg-zinc-900 text-zinc-300'
                "
              >
                {{ p.status === 'active' ? '上架' : '下架' }}
              </span>
            </div>
            <div class="col-span-2 flex justify-end">
              <button
                class="rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
                type="button"
                @click="openEdit(p)"
              >
                编辑
              </button>
            </div>
          </div>
          <div v-if="items.length === 0" class="p-4 text-sm text-zinc-400">暂无数据</div>
        </div>
      </div>

      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 md:items-center"
        @click.self="close"
      >
        <div class="w-full max-w-[720px] rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
          <div class="flex items-center justify-between">
            <div class="text-sm font-semibold">{{ editing?.id ? '编辑商品' : '新建商品' }}</div>
            <button
              class="rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
              type="button"
              @click="close"
            >
              关闭
            </button>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div class="md:col-span-2">
              <div class="text-xs text-zinc-400">标题</div>
              <input
                v-model="formTitle"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">SKU（可选）</div>
              <input
                v-model="formSku"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div>
              <div class="text-xs text-zinc-400">状态</div>
              <select
                v-model="formStatus"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              >
                <option value="active">上架</option>
                <option value="inactive">下架</option>
              </select>
            </div>
            <div class="md:col-span-2">
              <div class="text-xs text-zinc-400">外链（必填）</div>
              <input
                v-model="formUrl"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div class="md:col-span-2">
              <div class="text-xs text-zinc-400">标签（逗号分隔）</div>
              <input
                v-model="formTags"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
            <div class="md:col-span-2">
              <div class="text-xs text-zinc-400">描述（可选）</div>
              <textarea
                v-model="formDesc"
                rows="3"
                class="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-lime-400/60"
              />
            </div>
          </div>

          <div class="mt-4 flex flex-wrap items-center gap-2">
            <button
              class="rounded-xl bg-lime-400 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-lime-300"
              type="button"
              @click="save"
            >
              保存
            </button>
            <label
              class="inline-flex cursor-pointer items-center justify-center rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-2 text-sm text-zinc-300 transition hover:bg-zinc-900 hover:text-zinc-100"
            >
              {{ uploading ? '上传中…' : '上传图片' }}
              <input
                class="hidden"
                type="file"
                accept="image/*"
                multiple
                :disabled="uploading || !editing?.id"
                @change="onUploadImages"
              />
            </label>
            <div class="text-xs text-zinc-500">上传后回发到飞书会自动尝试把图片发出去</div>
          </div>

          <div v-if="editing?.images?.length" class="mt-4">
            <div class="text-xs text-zinc-400">图片</div>
            <div class="mt-2 grid grid-cols-3 gap-3 md:grid-cols-5">
              <div
                v-for="img in editing.images"
                :key="img.id"
                class="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40"
              >
                <img :src="img.url" class="h-24 w-full object-cover" />
                <button
                  class="absolute right-2 top-2 hidden rounded-lg bg-black/60 px-2 py-1 text-xs text-zinc-100 group-hover:block"
                  type="button"
                  @click="deleteImage(img.id)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

