<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { http } from '@/lib/http'

type Profile = {
  id: number
  email: string
  display_name: string | null
  role: string
  is_active: boolean
  date_joined: string
}

const auth = useAuthStore()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const profile = ref<Profile | null>(null)

const form = reactive({
  display_name: '',
})

const isDirty = computed(() => form.display_name !== (profile.value?.display_name || ''))

const joinedAt = computed(() => formatDateTime(profile.value?.date_joined ?? null))

function formatDateTime(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function loadProfile() {
  loading.value = true
  try {
    const { data } = await http.get<Profile>('/users/me/profile')
    profile.value = data
    form.display_name = data.display_name || ''
  } catch (err: any) {
    const status = err?.response?.status
    const msg = err?.response?.data?.detail || err?.message || '無法載入個人資料'
    if (status === 401) {
      ElMessage.error('請先登入以檢視個人資料')
      router.push('/login')
    } else {
      ElMessage.error(msg)
    }
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!profile.value || saving.value) return

  saving.value = true
  try {
    const { data } = await http.patch<Profile>('/users/me/profile', {
      display_name: form.display_name,
    })
    profile.value = data
    form.display_name = data.display_name || ''
    await auth.fetchMe()
    ElMessage.success('個人資料已更新')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '更新失敗'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!auth.me) {
    try {
      await auth.fetchMe()
    } catch {
      // 若抓取失敗，交由 loadProfile 重新處理
    }
  }
  await loadProfile()
})
</script>

<template>
  <div class="max-w-3xl space-y-4">
    <el-card v-loading="loading">
      <template #header>個人資料</template>

      <el-form label-width="96px" @submit.prevent>
        <el-form-item label="電子郵件">
          <span>{{ profile?.email || '-' }}</span>
        </el-form-item>

        <el-form-item label="顯示名稱">
          <el-input v-model="form.display_name" placeholder="輸入顯示名稱" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :disabled="!isDirty" :loading="saving" @click="handleSubmit">
            儲存
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="profile" v-loading="loading">
      <template #header>帳號資訊</template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="帳號狀態">
          <el-tag :type="profile.is_active ? 'success' : 'danger'">
            {{ profile.is_active ? '啟用中' : '已停用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="角色">
          {{ profile.role || '一般會員' }}
        </el-descriptions-item>
        <el-descriptions-item label="建立時間">
          {{ joinedAt }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>
