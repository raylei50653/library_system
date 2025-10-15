<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goToBooks() {
  router.push('/books')
}

function goToChat() {
  router.push('/chat')
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>歡迎來到圖書館系統</h1>
      <p>瀏覽館藏、管理借閱紀錄，還能追蹤收藏與訊息，打造個人的閱讀旅程。</p>

      <div class="actions">
        <el-button type="primary" size="large" @click="goToBooks">探索館藏</el-button>
        <el-button size="large" @click="goToChat">客服中心</el-button>
      </div>
    </section>

    <section class="features">
      <el-card class="feature-card" shadow="never">
        <h2>智能搜尋</h2>
        <p>使用篩選與排序，快速找到你需要的書目與分類。</p>
      </el-card>

      <el-card class="feature-card" shadow="never">
        <h2>借閱管理</h2>
        <p>掌握借閱與預約進度，避免逾期並即時收到通知。</p>
      </el-card>

      <el-card class="feature-card" shadow="never">
        <h2>個人收藏</h2>
        <p>將喜愛的書籍加入收藏清單，方便再次借閱或推薦好友。</p>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.hero {
  padding: 40px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 45px rgba(79, 70, 229, 0.25);
}

.hero h1 {
  font-size: 36px;
  margin-bottom: 16px;
}

.hero p {
  font-size: 18px;
  margin-bottom: 24px;
  max-width: 540px;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.feature-card {
  border-radius: 16px;
  padding: 24px;
}

.feature-card h2 {
  font-size: 20px;
  margin-bottom: 12px;
  color: #1f2937;
}

.feature-card p {
  color: #4b5563;
  line-height: 1.6;
}
</style>
