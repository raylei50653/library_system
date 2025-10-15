<!-- src/features/chat/pages/ChatCenterView.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTickets, createTicket, type Ticket } from '../api'

const router = useRouter()

const loading = ref(false)
const creating = ref(false)
const tickets = ref<Ticket[]>([])
const total = ref(0)
const page = ref(1)

const showNewDialog = ref(false)
const newSubject = ref('')
const newContent = ref('')

async function fetchTickets() {
  loading.value = true
  try {
    const data = await listTickets({ mine: true, page: page.value })
    tickets.value = data.results
    total.value = data.count
  } catch (err: any) {
    if (err?.response?.status === 401) {
      ElMessage.error('尚未登入或登入已過期')
      router.push('/login')
    } else {
      ElMessage.error('載入票單失敗')
    }
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  const subject = newSubject.value.trim()
  if (!subject || creating.value) return
  creating.value = true
  try {
    // 後端回傳多半是 { ticket_id: number }，也可能被你在 api 層轉成 { id }
    const t: any = await createTicket({
      subject,
      content: newContent.value || undefined,
    })
    ElMessage.success('已建立票單')
    showNewDialog.value = false
    newSubject.value = ''
    newContent.value = ''
    const tid = t?.id ?? t?.ticket_id // 兼容兩種回傳
    if (!tid) {
      ElMessage.warning('建立成功，但未取得票單 ID，已重新整理列表')
      fetchTickets()
      return
    }
    router.push(`/chat/tickets/${tid}`)
  } catch (err: any) {
    if (err?.response?.status === 401) {
      ElMessage.error('尚未登入或登入已過期')
      router.push('/login')
    } else if (err?.response?.data?.detail) {
      ElMessage.error(`建立失敗：${err.response.data.detail}`)
    } else {
      ElMessage.error('建立失敗，請稍後再試')
    }
  } finally {
    creating.value = false
  }
}

function goto(t: Ticket) {
  router.push(`/chat/tickets/${t.id}`)
}

onMounted(fetchTickets)
</script>

<template>
  <div class="p-4 max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">客服中心</h1>
      <el-button type="primary" @click="showNewDialog = true">新建票單</el-button>
    </div>

    <el-table :data="tickets" v-loading="loading" stripe>
      <el-table-column prop="id" label="#" width="80" />
      <el-table-column prop="subject" label="主旨" min-width="240" />
      <el-table-column prop="status" label="狀態" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'open' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新時間" width="200">
        <template #default="{ row }">
          {{ new Date(row.updated_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="goto(row)">查看</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <div class="py-10 text-gray-500">目前沒有票單</div>
      </template>
    </el-table>

    <div class="mt-3 flex justify-end">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="10"
        :current-page="page"
        @current-change="(p:number)=>{ page=p; fetchTickets() }"
      />
    </div>

    <!-- 新建票單 -->
    <el-dialog v-model="showNewDialog" title="新建票單" width="520px">
      <el-form label-width="72px" @submit.prevent>
        <el-form-item label="主旨">
          <el-input v-model="newSubject" placeholder="請描述問題主旨" />
        </el-form-item>
        <el-form-item label="內容">
          <el-input v-model="newContent" type="textarea" :rows="5" placeholder="可先附上背景資訊（選填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="onCreate">建立</el-button>
      </template>
    </el-dialog>
  </div>
</template>
