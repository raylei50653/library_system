// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import router from '@/app/router'   // ✅ 這裡改成 default import
import App from './App.vue'

const app = createApp(App)

// 掛載全域套件
app.use(createPinia())
app.use(ElementPlus)
app.use(router)

app.mount('#app')
