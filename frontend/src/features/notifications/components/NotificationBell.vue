<!-- src/features/notifications/components/NotificationBell.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell } from '@element-plus/icons-vue'
import { listNotifications } from '@/features/notifications/api'
import type { Notification } from '@/types/notification'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'

const router = useRouter()
const store = useNotificationsStore()
const loading = ref(false)
const latest = ref<Notification[]>([])

async function loadLatest() {
  loading.value = true
  try {
    // 只抓未讀最新 5 筆（若後端未支援 page_size，依預設亦可）
    const res = await listNotifications({ is_read: false, page: 1 })
    latest.value = res.results.slice(0, 5)
  } catch {
    ElMessage.error('載入通知失敗')
  } finally {
    loading.value = false
  }
}

function goCenter() {
  router.push('/notifications')
}

onMounted(() => {
  store.ensurePolling(30000)
  loadLatest()
})
</script>

<template>
  <el-dropdown trigger="click" @visible-change="val => val && loadLatest()">
    <span class="el-dropdown-link cursor-pointer inline-flex items-center gap-1">
      <el-badge :value="store.unread" :hidden="!store.hasUnread" class="align-middle">
        <el-icon class="text-[20px]"><Bell /></el-icon>
      </el-badge>
    </span>
    <template #dropdown>
      <el-dropdown-menu class="min-w-[280px] max-w-[360px]">
        <div class="px-3 py-2 font-semibold">通知</div>
        <el-divider class="my-1" />
        <div v-if="loading" class="px-3 py-2 text-gray-500">載入中…</div>
        <template v-else>
          <div v-if="latest.length === 0" class="px-3 py-2 text-gray-500">目前沒有未讀通知</div>
          <div v-else class="max-h-[320px] overflow-auto">
            <div v-for="n in latest" :key="n.id" class="px-3 py-2 hover:bg-gray-50">
              <div class="text-sm font-medium line-clamp-2">{{ n.title }}</div>
              <div class="text-xs text-gray-500 line-clamp-2">
                {{ (n.body ?? n.message ?? '') || '（無內文）' }}
              </div>
              <div class="text-[11px] text-gray-400 mt-0.5">
                {{ new Date(n.created_at).toLocaleString() }}
              </div>
            </div>
          </div>
        </template>
        <el-divider class="my-1" />
        <div class="px-3 py-2">
          <el-button type="primary" size="small" class="w-full" @click="goCenter">前往通知中心</el-button>
        </div>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
