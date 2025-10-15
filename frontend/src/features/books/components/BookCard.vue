<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { Book } from '@/types/book'
import { borrowBook, reserveBook } from '@/features/loans/api'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

// 收藏 API（請確認檔案存在：src/features/favorites/api.ts）
import { addFavorite, removeFavorite, isFavorite } from '@/features/favorites/api'

const props = defineProps<{ book: Book }>()
const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)     // 借閱/預約 loading
const favLoading = ref(false)  // 收藏 loading
const isFav = ref(false)

const hasStock = computed(() => (props.book.available_count ?? 0) > 0)
const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  // 未登入就不查收藏狀態（節省請求）；登入才查一次
  if (auth.me) {
    try {
      isFav.value = await isFavorite(props.book.id)
    } catch { /* ignore */ }
  }
})

async function requireLogin(tip: string) {
  if (!auth.me) {
    ElMessage.info(tip)
    router.push('/login')
    return false
  }
  return true
}

async function handleBorrow() {
  if (!(await requireLogin('請先登入以借閱'))) return
  loading.value = true
  try {
    await borrowBook(props.book.id)
    ElMessage.success('借閱成功')
    emit('changed')
  } catch (e: any) {
    if (e?.response?.status === 409) {
      ElMessage.info('目前無庫存，已切換為預約流程')
      await handleReserve()
    } else {
      ElMessage.error(e?.response?.data?.detail || '借閱失敗')
    }
  } finally {
    loading.value = false
  }
}

async function handleReserve() {
  if (!(await requireLogin('請先登入以預約'))) return
  loading.value = true
  try {
    await reserveBook(props.book.id)
    ElMessage.success('已加入預約候補清單')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '預約失敗')
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!(await requireLogin('請先登入以使用收藏'))) return
  favLoading.value = true
  try {
    if (isFav.value) {
      await removeFavorite(props.book.id)
      isFav.value = false
      ElMessage.success('已取消收藏')
    } else {
      await addFavorite(props.book.id)
      isFav.value = true
      ElMessage.success('已加入收藏')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '收藏操作失敗')
  } finally {
    favLoading.value = false
  }
}
</script>

<template>
  <el-card shadow="hover" class="mb-3">
    <div class="flex justify-between items-start">
      <div>
        <div class="text-base font-semibold">{{ book.title }}</div>
        <div class="text-sm text-gray-600" v-if="book.author">{{ book.author }}</div>
        <div class="mt-1">
          <el-tag v-if="hasStock" type="success">可借（{{ book.available_count }}）</el-tag>
          <el-tag v-else type="info">暫無庫存</el-tag>
        </div>
      </div>

      <div class="flex gap-2">
        <!-- 收藏 / 取消收藏 -->
        <el-button
          size="small"
          :type="isFav ? 'danger' : 'default'"
          :loading="favLoading"
          plain
          @click="toggleFavorite"
          data-test-id="fav-btn"
        >
          {{ isFav ? '取消收藏' : '加入收藏' }}
        </el-button>

        <!-- 借閱 / 預約 -->
        <el-button
          size="small"
          type="primary"
          :loading="loading"
          @click="hasStock ? handleBorrow() : handleReserve()"
        >
          {{ hasStock ? '借閱' : '預約' }}
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.el-card { border-radius: 12px; }
</style>
