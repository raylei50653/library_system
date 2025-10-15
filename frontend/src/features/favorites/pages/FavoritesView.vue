<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getFavorites, removeFavorite } from '../api'
import { ElMessageBox, ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref<any[]>([])

async function fetchFavorites() {
  loading.value = true
  try {
    items.value = await getFavorites()
  } finally {
    loading.value = false
  }
}

async function handleRemove(bookId: number) {
  await ElMessageBox.confirm('確定要移除此收藏嗎？', '提示', { type: 'warning' })
  await removeFavorite(bookId)
  ElMessage.success('已移除收藏')
  fetchFavorites()
}

onMounted(fetchFavorites)
</script>

<template>
  <div class="p-6">
    <h2 class="text-xl font-bold mb-4">我的收藏</h2>
    <el-empty v-if="!items.length && !loading" description="目前沒有收藏" />
    <el-row :gutter="16" v-else>
      <el-col :span="6" v-for="fav in items" :key="fav.id">
        <el-card>
          <h3>{{ fav.book.title }}</h3>
          <p>{{ fav.book.author }}</p>
          <el-button type="danger" size="small" @click="handleRemove(fav.book.id)">移除</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
