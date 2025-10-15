<!-- src/App.vue -->
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, RouterLink, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ArrowDown } from '@element-plus/icons-vue'

// 穩定載入 logo（避免別名解析問題）
const logoUrl = new URL('./assets/logo.svg', import.meta.url).href

// 狀態
const router = useRouter()
const auth = useAuthStore()

const isLoggedIn = computed<boolean>(() => !!auth.me)
const userName = computed<string>(() => auth.me?.display_name || auth.me?.email || '使用者')

// 有 token 時視為可能登入狀態（搭配 fetchMe 還原）
const hasToken = computed<boolean>(() => !!localStorage.getItem('access'))
const isAuthed = computed<boolean>(() => isLoggedIn.value || hasToken.value)

// 啟動時若偵測到 token 但沒有 me，嘗試拉取
onMounted(async () => {
  if (hasToken.value && !auth.me) {
    try { await auth.fetchMe() } catch { /* ignore */ }
  }
})

// 登出
async function handleLogout() {
  const ok = await ElMessageBox.confirm('確定要登出嗎？', '登出確認', {
    confirmButtonText: '確定',
    cancelButtonText: '取消',
    type: 'warning',
  }).catch(() => false)
  if (ok) {
    auth.logoutLocal()
    router.push('/login')
  }
}

// 暴露給模板/型別系統
defineExpose({ isAuthed, hasToken, isLoggedIn, userName })
</script>

<template>
  <!-- 外層縱向：Header + 主內容 -->
  <el-container class="app-root">
    <!-- 頂部 Box（滿寬） -->
    <el-header height="64px" class="app-header">
      <div class="header-left">
        <img :src="logoUrl" alt="logo" class="logo" />
        <span class="brand">Library System</span>
      </div>

      <div class="header-right">
        <!-- 未登入：顯示登入 -->
        <el-button
          v-if="!isAuthed"
          type="primary"
          size="small"
          @click="router.push('/login')"
        >
          登入
        </el-button>

        <!-- 已登入：顯示使用者下拉 -->
        <el-dropdown v-else trigger="click">
          <span class="el-dropdown-link user-chip">
            <span class="avatar">{{ (userName[0] || 'U').toUpperCase() }}</span>
            <span class="uname">{{ userName }}</span>
            <el-icon class="ml-1"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/profile')">個人資料</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主內容區：左側固定 Aside + 右側 Main -->
    <el-container class="app-body">
      <!-- 固定的側欄（左） -->
      <el-aside width="240px" class="app-aside">
        <nav class="menu">
          <RouterLink to="/" class="item" active-class="active">首頁</RouterLink>
          <RouterLink to="/books" class="item" active-class="active">館藏</RouterLink>
          <RouterLink to="/loans" class="item" active-class="active">借閱紀錄</RouterLink>
          <RouterLink to="/favorites" class="item" active-class="active">收藏</RouterLink>
          <RouterLink to="/notifications" class="item" active-class="active">通知</RouterLink>
          <RouterLink to="/chat" class="item" active-class="active">客服中心</RouterLink>
        </nav>

        <!-- 個人區塊（置底） -->
        <div class="me-box" v-if="isAuthed">
          <div class="me-title">個人資料</div>
          <div class="me-content">
            <div class="me-name">
              <span class="avatar small">{{ (userName[0] || 'U').toUpperCase() }}</span>
              {{ userName }}
            </div>
            <div class="me-actions">
              <el-button text size="small" @click="router.push('/profile')">查看 / 編輯</el-button>
              <el-button text size="small" type="danger" @click="handleLogout">登出</el-button>
            </div>
          </div>
        </div>

        <div class="me-box" v-else>
          <div class="me-title">個人資料</div>
          <div class="me-content">
            <div class="me-name text-muted">尚未登入</div>
            <el-button text size="small" type="primary" @click="router.push('/login')">前往登入</el-button>
          </div>
        </div>
      </el-aside>

      <!-- 右側主視圖：用路由渲染（/books -> BooksListView.vue） -->
      <el-main class="app-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
/* 讓 Header 置頂、Aside 固定、Main 佔滿剩餘寬度 */
.app-root {
  min-height: 100vh;
  padding: 0;
  margin: 0;
  background: #f6f7fb;
}

/* Header */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-inline: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo {
  width: 28px;
  height: 28px;
}
.brand {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 0.2px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-chip {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

/* 內容容器 */
.app-body {
  position: relative;
  padding-top: 0;
}

/* 側欄固定在左邊，從 header 下緣開始到視窗底 */
.app-aside {
  position: fixed;
  top: 64px;            /* 等同 header 高度 */
  bottom: 0;
  left: 0;
  width: 240px !important;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  padding: 12px 8px 80px; /* 底部留空給 me-box */
  box-sizing: border-box;
  overflow-y: auto;
}

/* 側欄選單 */
.menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.menu .item {
  padding: 10px 12px;
  border-radius: 8px;
  color: #374151;
  text-decoration: none;
  font-size: 14px;
}
.menu .item:hover {
  background: #f3f4f6;
}
.menu .item.active {
  background: #edf2ff;
  color: #1f3dc3;
  font-weight: 600;
}

/* 個人資料框（固定在側欄底部） */
.me-box {
  position: fixed;
  left: 0;
  bottom: 0;
  width: 240px;
  box-sizing: border-box;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  padding: 10px 12px;
}
.me-title {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}
.me-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.me-name {
  font-weight: 600;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.text-muted {
  color: #9ca3af;
}
.me-actions :deep(.el-button) + :deep(.el-button) {
  margin-left: 4px;
}

/* 小頭像 */
.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: #e5e7eb;
  margin-right: 8px;
}
.avatar.small { width: 20px; height: 20px; font-size: 11px; margin-right: 6px; }
.uname { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 主內容：往右偏移等同側欄寬度，避免被覆蓋 */
.app-main {
  margin-left: 240px;
  padding: 16px;
}
</style>
