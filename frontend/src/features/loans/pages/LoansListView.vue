<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http } from '@/lib/http'

type LoanStatus = 'pending' | 'active' | 'returned' | 'overdue' | 'canceled'

type Loan = {
  id: number
  book: number
  book_title: string
  status: LoanStatus
  loaned_at: string | null
  due_at: string | null
  returned_at: string | null
  renew_count: number
  created_at: string
}

type LoanListResponse = {
  count: number
  results: Loan[]
}

const loading = ref(false)
const actionState = ref<{ id: number | null; type: 'renew' | 'return' | null }>({
  id: null,
  type: null,
})

const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const statusFilter = ref<'all' | LoanStatus>('all')
const items = ref<Loan[]>([])

const statusOptions: Array<{ value: 'all' | LoanStatus; label: string }> = [
  { value: 'all', label: '全部狀態' },
  { value: 'pending', label: '待處理' },
  { value: 'active', label: '借閱中' },
  { value: 'overdue', label: '逾期' },
  { value: 'returned', label: '已歸還' },
  { value: 'canceled', label: '已取消' },
]

const statusMeta: Record<LoanStatus, { label: string; type: 'info' | 'success' | 'warning' | 'danger' | '' }> = {
  pending: { label: '待處理', type: 'info' },
  active: { label: '借閱中', type: 'success' },
  overdue: { label: '逾期', type: 'danger' },
  returned: { label: '已歸還', type: 'info' },
  canceled: { label: '已取消', type: '' },
}

const itemsView = computed(() =>
  items.value.map((loan) => ({
    ...loan,
    status_label: statusMeta[loan.status].label,
    status_type: statusMeta[loan.status].type,
    loaned_at_fmt: formatDateTime(loan.loaned_at),
    due_at_fmt: formatDateTime(loan.due_at),
    returned_at_fmt: formatDateTime(loan.returned_at),
    created_at_fmt: formatDateTime(loan.created_at),
  })),
)

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

async function fetchLoans() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (statusFilter.value !== 'all') params.status = statusFilter.value

    const { data } = await http.get<LoanListResponse>('/api/loans/', { params })
    items.value = data.results
    total.value = data.count
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '無法載入借閱紀錄'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function canRenew(loan: Loan) {
  return loan.status === 'active'
}

function canReturn(loan: Loan) {
  return loan.status === 'active' || loan.status === 'overdue'
}

async function handleRenew(loan: Loan) {
  const ok = await ElMessageBox.confirm(
    `確定要續借「${loan.book_title}」嗎？`,
    '續借確認',
    {
      confirmButtonText: '確定',
      cancelButtonText: '取消',
      type: 'warning',
    },
  ).catch(() => false)
  if (!ok) return

  actionState.value = { id: loan.id, type: 'renew' }
  try {
    await http.post(`/api/loans/${loan.id}/renew/`)
    ElMessage.success('續借成功')
    await fetchLoans()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '續借失敗'
    ElMessage.error(msg)
  } finally {
    actionState.value = { id: null, type: null }
  }
}

async function handleReturn(loan: Loan) {
  const ok = await ElMessageBox.confirm(
    `確定要歸還「${loan.book_title}」嗎？`,
    '歸還確認',
    {
      confirmButtonText: '確定',
      cancelButtonText: '取消',
      type: 'warning',
    },
  ).catch(() => false)
  if (!ok) return

  actionState.value = { id: loan.id, type: 'return' }
  try {
    await http.post(`/api/loans/${loan.id}/return_/`)
    ElMessage.success('歸還狀態已更新')
    await fetchLoans()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || '歸還失敗'
    ElMessage.error(msg)
  } finally {
    actionState.value = { id: null, type: null }
  }
}

function handlePageChange(p: number) {
  page.value = p
  fetchLoans()
}

function handlePageSizeChange(sz: number) {
  pageSize.value = sz
  page.value = 1
  fetchLoans()
}

function handleStatusChange(val: 'all' | LoanStatus) {
  statusFilter.value = val
}

watch(statusFilter, () => {
  page.value = 1
  fetchLoans()
})

onMounted(() => {
  fetchLoans()
})
</script>

<template>
  <div class="space-y-4">
    <el-card>
      <div class="flex flex-wrap items-center gap-3">
        <el-select
          :model-value="statusFilter"
          placeholder="選擇狀態"
          class="w-44"
          @change="handleStatusChange"
        >
          <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>

        <el-button :loading="loading" @click="fetchLoans">重新整理</el-button>
      </div>
    </el-card>

    <el-card>
      <el-table :data="itemsView" v-loading="loading" border stripe>
        <el-table-column prop="book_title" label="館藏" min-width="200" show-overflow-tooltip />
        <el-table-column label="狀態" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status_type">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="loaned_at_fmt" label="借出時間" min-width="170" />
        <el-table-column prop="due_at_fmt" label="到期時間" min-width="170" />
        <el-table-column prop="returned_at_fmt" label="歸還時間" min-width="170" />
        <el-table-column prop="renew_count" label="續借次數" width="110" align="center" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button
                size="small"
                type="primary"
                :disabled="!canRenew(row)"
                :loading="actionState.id === row.id && actionState.type === 'renew'"
                @click="handleRenew(row)"
              >
                續借
              </el-button>
              <el-button
                size="small"
                type="success"
                :disabled="!canReturn(row)"
                :loading="actionState.id === row.id && actionState.type === 'return'"
                @click="handleReturn(row)"
              >
                歸還
              </el-button>
            </el-space>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="目前沒有借閱紀錄" />
        </template>
      </el-table>

      <div class="flex justify-end pt-4" v-if="total > 0">
        <el-pagination
          layout="total, sizes, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          background
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.w-44 {
  width: 11rem;
}
</style>
