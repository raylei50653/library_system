<!-- src/features/auth/pages/LoginView.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

type LoginForm = { email: string; password: string }
const formRef = ref<FormInstance>()
const form = ref<LoginForm>({ email: '', password: '' })
const loading = ref(false)

const rules: FormRules<LoginForm> = {
  email: [
    { required: true, message: '請輸入 Email', trigger: 'blur' },
    { type: 'email', message: 'Email 格式不正確', trigger: ['blur', 'change'] },
  ],
  password: [{ required: true, message: '請輸入密碼', trigger: 'blur' }],
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await auth.login(form.value.email, form.value.password)
      ElMessage.success('登入成功')
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    } catch {
      ElMessage.error('登入失敗，請確認帳密')
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <!-- 全螢幕置中 -->
  <div class="auth-wrap">
    <!-- 卡片：Element Plus -->
    <el-card class="auth-card" shadow="hover">
      <div class="auth-header">
        <h1 class="auth-title">登入</h1>
        <p class="auth-subtitle">進入圖書管理系統</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="Email" prop="email">
          <el-input
            v-model="form.email"
            type="email"
            autocomplete="username"
            clearable
            placeholder="you@example.com"
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item label="密碼" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            show-password
            clearable
            placeholder="請輸入密碼"
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="btn-full">
            登入
          </el-button>
        </el-form-item>

        <div class="auth-footer">
          還沒有帳號？
          <router-link to="/register">前往註冊</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
/* 版面：全螢幕置中 + 淡灰背景 */
.auth-wrap {
  min-height: 60vh;
  display: grid;
  place-items: center;
  padding: 48px 16px;
  background: #f5f7fa; /* Element Plus 默認灰底 */
}

/* 卡片尺寸與圓角、陰影（el-card 會有預設邊框與陰影） */
.auth-card {
  width: 360px;
  max-width: 94vw;
  border-radius: 16px;
}

/* 標題區 */
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

/* 按鈕鋪滿寬度 */
.btn-full {
  width: 100%;
}

/* 底部小字 */
.auth-footer {
  text-align: center;
  color: #606266;
  font-size: 13px;
}
</style>
