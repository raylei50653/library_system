<!-- src/features/chat/pages/TicketDetailView.vue -->
<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listMessages, postMessage, aiReply, type Message } from '../api'

const route = useRoute()
const router = useRouter()
const rawId = Number(route.params.id ?? route.query.ticket_id)
const ticketId = Number.isFinite(rawId) ? rawId : null

const loading = ref(false)
const sending = ref(false)
const page = ref(1)
const pageSize = ref(100)
const messages = ref<Message[]>([])
const input = ref('')

const listEl = ref<HTMLElement | null>(null)
function scrollToBottom() {
  nextTick(() => {
    const el = listEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function fetchMessages() {
  if (!ticketId) return
  loading.value = true
  try {
    const { results } = await listMessages(ticketId, page.value, pageSize.value)
    messages.value = results
    scrollToBottom()
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 401) {
      ElMessage.error('尚未登入或登入已過期')
      router.push('/login')
    } else if (code === 403) {
      ElMessage.error('沒有權限檢視此票單')
      router.push('/chat')
    } else {
      ElMessage.error('載入訊息失敗')
    }
  } finally {
    loading.value = false
  }
}

async function sendHuman() {
  const text = input.value.trim()
  if (!ticketId || !text || sending.value) return
  sending.value = true
  try {
    await postMessage(ticketId, text)
    input.value = ''
    await fetchMessages()
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 401) {
      ElMessage.error('尚未登入或登入已過期')
      router.push('/login')
    } else if (code === 403) {
      ElMessage.error('沒有權限在此票單發言')
    } else {
      ElMessage.error('送出失敗')
    }
  } finally {
    sending.value = false
  }
}

/** 單次 AI 回覆（同步）— 走 POST /chat/ai/reply/ */
async function askAIOnce() {
  const text = input.value.trim()
  if (!ticketId || !text || sending.value) return
  sending.value = true
  try {
    await aiReply(ticketId, text)
    input.value = ''
    await fetchMessages()
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 401) {
      ElMessage.error('尚未登入或登入已過期')
      router.push('/login')
    } else if (code === 403) {
      ElMessage.error('沒有權限在此票單請求 AI 回覆')
    } else if (err?.response?.data?.detail) {
      ElMessage.error(`發送失敗：${err.response.data.detail}`)
    } else {
      ElMessage.error('發送失敗')
    }
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  if (!ticketId) {
    ElMessage.error('票單編號無效')
    router.push('/chat')
    return
  }
  fetchMessages()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center justify-between p-3 border-b">
      <h1 class="text-lg font-semibold">客服單 #{{ ticketId ?? '—' }}</h1>
      <div class="text-sm text-gray-500">共 {{ messages.length }} 則訊息</div>
    </div>

    <div ref="listEl" class="flex-1 overflow-y-auto p-3 space-y-3">
      <el-skeleton :loading="loading" animated>
        <template #default>
          <div
            v-for="m in messages"
            :key="m.id"
            class="max-w-3xl"
            :class="m.is_ai ? 'self-start' : 'self-end ml-auto'"
          >
            <div
              class="rounded-lg px-3 py-2 whitespace-pre-wrap"
              :class="m.is_ai ? 'bg-gray-100' : 'bg-blue-500 text-white'"
            >
              {{ m.content }}
            </div>
            <div class="text-[12px] text-gray-400 mt-1">
              {{ new Date(m.created_at).toLocaleString() }}
            </div>
          </div>
        </template>
        <template #template>
          <el-skeleton-item variant="text" style="width: 60%" />
          <el-skeleton-item variant="text" style="width: 40%" />
          <el-skeleton-item variant="text" style="width: 70%" />
        </template>
      </el-skeleton>
    </div>

    <div class="p-3 border-t">
      <el-form @submit.prevent="askAIOnce" class="flex gap-2">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="輸入訊息…（Enter 送出、Shift+Enter 換行）"
          @keydown.enter.exact.prevent="askAIOnce"
        />
        <el-button :disabled="sending" @click="sendHuman">只送出</el-button>
        <el-button type="success" :loading="sending" @click="askAIOnce">AI 回覆</el-button>
      </el-form>
    </div>
  </div>
</template>
