// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import router from '@/app/router'   // ✅ 這裡改成 default import
import { storage } from '@/lib/storage'
import App from './App.vue'

const clearTokensOnUnload = () => {
  storage.remove('access')
  storage.remove('refresh')
}

if (typeof window !== 'undefined') {
  window.removeEventListener('beforeunload', clearTokensOnUnload)
  window.addEventListener('beforeunload', clearTokensOnUnload)
}

const app = createApp(App)

// 掛載全域套件
app.use(createPinia())
app.use(ElementPlus)
app.use(router)

app.mount('#app')
