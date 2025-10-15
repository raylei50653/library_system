<!-- src/features/auth/pages/RegisterView.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { AxiosError } from 'axios'
import { env } from '@/config/env'
import { http } from '@/lib/http'

const router = useRouter()

type RegisterForm = { display_name: string; email: string; password: string }
const formRef = ref<FormInstance>()
const form = ref<RegisterForm>({ display_name: '', email: '', password: '' })
const loading = ref(false)
const signupEnabled = ref(true)

onMounted(() => {
  // env.ENABLE_SIGNUP 允許是 string | boolean，統一轉成布林
  const flag = env.ENABLE_SIGNUP
  signupEnabled.value =
    typeof flag === 'string' ? flag === 'true' || flag === '1' : !!flag
})

const rules: FormRules<RegisterForm> = {
  display_name: [
    { min: 0, max: 32, message: '顯示名稱需小於 32 字元', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '請輸入 Email', trigger: 'blur' },
    { type: 'email', message: 'Email 格式不正確', trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: '請輸入密碼', trigger: 'blur' },
    { min: 8, message: '密碼至少 8 碼', trigger: 'blur' },
  ],
}

function extractErrorMessage(data: unknown): string | null {
  if (!data) return null
  if (typeof data === 'string') return data

  if (typeof data === 'object') {
    const detail = data as Record<string, unknown>
    const directDetail = detail.detail
    if (typeof directDetail === 'string') return directDetail

    for (const value of Object.values(detail)) {
      if (typeof value === 'string') return value
      if (Array.isArray(value)) {
        const first = value.find((item) => typeof item === 'string')
        if (first) return first
      }
    }
  }

  return null
}

async function onSubmit() {
  if (!signupEnabled.value || !formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await http.post(`/auth/register/`, {
        email: form.value.email,
        password: form.value.password,
        display_name: form.value.display_name || undefined,
      })
      ElMessage.success('註冊成功，請登入')
      router.push('/login')
    } catch (error) {
      const axiosError = error as AxiosError
      const message = extractErrorMessage(axiosError.response?.data)
      ElMessage.error(message ?? '註冊失敗，請確認資料或稍後再試')
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <div class="auth-wrap">
    <el-card class="auth-card" shadow="hover">
      <div class="auth-header">
        <h1 class="auth-title">註冊</h1>
        <p class="auth-subtitle">建立你的圖書管理系統帳號</p>
      </div>

      <el-alert
        v-if="!signupEnabled"
        type="warning"
        show-icon
        :closable="false"
        class="mb-3"
        title="目前已停用自助註冊，請聯繫管理員建立帳號"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        :disabled="!signupEnabled"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="顯示名稱（選填）" prop="display_name">
          <el-input
            v-model="form.display_name"
            placeholder="你想被顯示的名字"
            clearable
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item label="Email" prop="email">
          <el-input
            v-model="form.email"
            type="email"
            autocomplete="username"
            placeholder="you@example.com"
            clearable
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item label="密碼" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            show-password
            placeholder="請輸入密碼（至少 8 碼）"
            clearable
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="btn-full"
          >
            建立帳號
          </el-button>
        </el-form-item>

        <div class="auth-footer">
          已有帳號？
          <router-link to="/login">前往登入</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 60vh;
  display: grid;
  place-items: center;
  padding: 48px 16px;
  background: #f5f7fa;
}
.auth-card {
  width: 360px;
  max-width: 94vw;
  border-radius: 16px;
}
.auth-header {
  text-align: center;
  margin-bottom: 16px;
}
.auth-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.auth-subtitle {
  margin: 6px 0 0 0;
  color: #909399;
  font-size: 13px;
}
.btn-full {
  width: 100%;
}
.auth-footer {
  text-align: center;
  color: #606266;
  font-size: 13px;
}
.mb-3 { margin-bottom: 12px; }
</style>
