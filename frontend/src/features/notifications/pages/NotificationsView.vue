<!-- src/features/notifications/pages/NotificationsView.vue -->
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '../api'
import type { Notification } from '@/types/notification'
import type { Paginated } from '@/types/base'
import { useNotificationsStore } from '@/stores/notifications'

type FilterTab = 'all' | 'unread' | 'read'

const store = useNotificationsStore()
const loading = ref(false)
const items = ref<Notification[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const tab = ref<FilterTab>('all')

function toParams() {
  const params: any = { page: page.value }
  if (tab.value === 'unread') params.is_read = false
  if (tab.value === 'read') params.is_read = true
  return params
}

async function load() {
  loading.value = true
  try {
    const data: Paginated<Notification> = await listNotifications(toParams())
    items.value = data.results
    total.value = data.count
  } catch {
    ElMessage.error('載入通知失敗')
  } finally {
    loading.value = false
  }
}

async function onMarkRead(n: Notification) {
  if (n.is_read) return
  try {
    await markNotificationRead(n.id)
    n.is_read = true
    store.dec() // 同步 badge
    ElMessage.success('已標記為已讀')
  } catch {
    ElMessage.error('操作失敗')
  }
}

async function onMarkAll() {
  try {
    await ElMessageBox.confirm('確定要將所有未讀通知標記為已讀嗎？', '全部標記為已讀', {
      confirmButtonText: '確定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }

  try {
    await markAllNotificationsRead()
    // 標記畫面中的未讀為已讀
    items.value.forEach(n => (n.is_read = true))
    store.setZero()
    ElMessage.success('已全部標記為已讀')
    load()
  } catch {
    ElMessage.error('操作失敗')
  }
}

watch([tab, page], () => load())
onMounted(() => {
  store.ensurePolling()
  load()
})
</script>

<template>
  <div class="p-4">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <el-segmented v-model="tab" :options="[
          { label: '全部', value: 'all' },
          { label: '未讀', value: 'unread' },
          { label: '已讀', value: 'read' },
        ]" size="small" />
        <span v-if="tab === 'unread' && store.firstLoaded" class="text-sm text-gray-500">
          未讀：{{ store.unread }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <el-button size="small" @click="load" :loading="loading">重新整理</el-button>
        <el-button size="small" type="primary" plain @click="onMarkAll">全部標為已讀</el-button>
      </div>
    </div>

    <el-skeleton :loading="loading" animated>
      <el-empty v-if="!items.length && !loading" description="沒有任何通知" />
      <div v-else class="space-y-2">
        <el-card v-for="n in items" :key="n.id" :class="{ 'opacity-70': n.is_read }">
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="font-medium text-base truncate">{{ n.title }}</div>
              <div class="text-sm text-gray-600 whitespace-pre-line mt-1">
                {{ (n.body ?? n.message ?? '') || '（無內文）' }}
              </div>
              <div class="text-xs text-gray-400 mt-1">{{ new Date(n.created_at).toLocaleString() }}</div>
            </div>
            <div class="flex-shrink-0">
              <el-button size="small" type="success" plain :disabled="n.is_read" @click="onMarkRead(n)">
                標為已讀
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
    </el-skeleton>

    <div class="flex justify-center mt-4">
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        layout="prev, pager, next"
        :total="total"
      />
    </div>
  </div>
</template>
