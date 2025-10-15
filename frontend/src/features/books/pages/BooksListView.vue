<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/lib/http'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// ✅ 收藏 API
import { loadFavoritesOnce, addFavorite, removeFavorite } from '@/features/favorites/api'

type Category = { id: number; name: string; slug?: string }
type Book = {
  id: number
  title: string
  author?: string
  category?: Category | null
  status?: 'available' | 'unavailable' | string
  available_count?: number
}

const loading = ref(false)
const items = ref<Book[]>([])
const total = ref(0)

const page = ref(1)
const pageSize = ref(10)
const search = ref('')
const categories = ref<Category[]>([])
const categorySlug = ref<string | null>(null)
const ordering = ref<'title' | '-title' | 'author' | '-author'>('title')

const router = useRouter()
const auth = useAuthStore()
const actionRowId = ref<number | null>(null)

// ✅ 收藏狀態（整頁共用）
const favIds = ref<Set<number>>(new Set())
const favBusy = ref<number | null>(null)

let aborter: AbortController | null = null
let debounceTimer: number | null = null

function hasStock(row: Book) {
  if (typeof row.available_count === 'number') return row.available_count > 0
  return row.status === 'available'
}

function isFav(row: Book) {
  return favIds.value.has(row.id)
}

async function ensureLogin(tip: string) {
  if (!auth.me) {
    ElMessage.info(tip)
    router.push('/login')
    return false
  }
  return true
}

async function fetchBooks() {
  if (aborter) aborter.abort()
  aborter = new AbortController()
  loading.value = true
  try {
    const { data } = await http.get<{ count: number; results: Book[] }>('/api/books/', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        search: search.value || undefined,
        category: categorySlug.value || undefined,
        ordering: ordering.value || undefined,
      },
      signal: aborter.signal,
    })
    items.value = data.results
    total.value = data.count
  } catch (err: any) {
    if (err?.name !== 'CanceledError' && err?.code !== 'ERR_CANCELED') {
      const msg = err?.response?.data?.detail || err?.message || '載入失敗，稍後再試'
      ElMessage.error(msg)
    }
  } finally {
    loading.value = false
  }
}

async function fetchCategories() {
  try {
    const { data } = await http.get<Category[]>('/api/categories/')
    categories.value = data
  } catch {
    ElMessage.error('無法載入分類清單')
  }
}

async function handleBorrow(row: Book) {
  if (!(await ensureLogin('請先登入以借閱'))) return
  actionRowId.value = row.id
  try {
    await http.post(`/api/loans/`, { book_id: row.id })
    ElMessage.success('借閱成功')
    await fetchBooks()
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 409) {
      ElMessage.info('目前無庫存，已切換為預約流程')
      await handleReserve(row)
      return
    }
    if (code === 401) {
      ElMessage.info('登入逾時，請重新登入')
      router.push('/login')
      return
    }
    const msg = err?.response?.data?.detail || err?.message || '借閱失敗'
    ElMessage.error(msg)
  } finally {
    actionRowId.value = null
  }
}

async function handleReserve(row: Book) {
  if (!(await ensureLogin('請先登入以預約'))) return
  actionRowId.value = row.id
  try {
    await http.post(`/api/reservations/`, { book_id: row.id })
    ElMessage.success('已加入預約候補清單')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '預約失敗'
    ElMessage.error(msg)
  } finally {
    actionRowId.value = null
  }
}

// ✅ 收藏 / 取消收藏
async function toggleFavorite(row: Book) {
  if (!(await ensureLogin('請先登入以使用收藏'))) return
  favBusy.value = row.id
  try {
    if (isFav(row)) {
      await removeFavorite(row.id)
      favIds.value.delete(row.id)
      ElMessage.success('已取消收藏')
    } else {
      await addFavorite(row.id)
      favIds.value.add(row.id)
      ElMessage.success('已加入收藏')
    }
    // 觸發相依 UI 更新
    favIds.value = new Set(favIds.value)
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '收藏操作失敗'
    ElMessage.error(msg)
  } finally {
    favBusy.value = null
  }
}

function handleSearchNow() {
  page.value = 1
  fetchBooks()
}

function handleSearchDebounced() {
  if (debounceTimer) window.clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(() => {
    page.value = 1
    fetchBooks()
  }, 300)
}

function handlePageChange(p: number) {
  page.value = p
  fetchBooks()
}

function handlePageSizeChange(sz: number) {
  pageSize.value = sz
  page.value = 1
  fetchBooks()
}

function handleOrderingChange(val: typeof ordering.value) {
  ordering.value = val
  page.value = 1
  fetchBooks()
}

function handleCategoryChange(val: string | null) {
  categorySlug.value = val
  page.value = 1
  fetchBooks()
}

onMounted(async () => {
  await fetchCategories()
  await fetchBooks()
  // ✅ 若已登入，載入一次收藏清單（快取自 API 模組）
  if (auth.me) {
    try {
      favIds.value = new Set(await loadFavoritesOnce())
    } catch {
      // ignore：未登入或 API 失敗時略過收藏狀態
    }
  }
})

watch(search, handleSearchDebounced)

// 顯示用：分類名稱
const itemsView = computed(() =>
  items.value.map(b => ({
    ...b,
    category_name: b.category?.name ?? '-',
  })),
)
</script>

<template>
  <div class="space-y-4">
    <el-card>
      <div class="flex flex-wrap items-center gap-2">
        <el-input
          v-model="search"
          placeholder="關鍵字（書名／作者）"
          class="max-w-[260px]"
          clearable
        />

        <el-select
          :model-value="categorySlug"
          @change="handleCategoryChange"
          placeholder="選擇分類"
          class="w-56"
          clearable
        >
          <el-option
            v-for="c in categories"
            :key="c.slug || c.id"
            :label="c.name"
            :value="c.slug || String(c.id)"
          />
        </el-select>

        <el-select
          :model-value="ordering"
          @change="handleOrderingChange"
          placeholder="排序"
          class="w-36"
        >
          <el-option label="書名 ↑" value="title" />
          <el-option label="書名 ↓" value="-title" />
          <el-option label="作者 ↑" value="author" />
          <el-option label="作者 ↓" value="-author" />
        </el-select>

        <el-button type="primary" @click="handleSearchNow">搜尋</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="itemsView" v-loading="loading" border stripe>
        <el-table-column prop="title" label="書名" min-width="240" />
        <el-table-column prop="author" label="作者" min-width="160" />
        <el-table-column prop="category_name" label="分類" width="140" />
        <el-table-column prop="status" label="狀態" width="120" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <!-- ✅ 收藏 / 取消收藏 -->
            <el-button
              size="small"
              :type="isFav(row) ? 'danger' : 'default'"
              :loading="favBusy === row.id"
              plain
              class="mr-2"
              @click="toggleFavorite(row)"
            >
              {{ isFav(row) ? '取消收藏' : '加入收藏' }}
            </el-button>

            <!-- 借閱 / 預約 -->
            <el-button
              size="small"
              type="primary"
              :loading="actionRowId === row.id"
              @click="hasStock(row) ? handleBorrow(row) : handleReserve(row)"
            >
              {{ hasStock(row) ? '借閱' : '預約' }}
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <div class="py-8 text-gray-500">沒有符合條件的資料</div>
        </template>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination
          background
          layout="sizes, prev, pager, next, total"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          :page-sizes="[10, 20, 50, 100]"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>
