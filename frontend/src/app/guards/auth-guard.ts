// src/app/guards/auth-guard.ts
import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { storage } from '@/lib/storage'

export function setupAuthGuard(router: Router) {
  router.beforeEach(async (to, _from, next) => {
    const auth = useAuthStore()
    const isLoggedIn = !!auth.me
    const token = storage.get('access')

    // 不需要登入的頁面
    const publicPages = ['/login', '/register']
    const isPublic = publicPages.includes(to.path)

    // 若未登入但有 token（重新整理的情況）
    if (!isLoggedIn && token) {
      try {
        await auth.fetchMe()
      } catch {
        auth.logoutLocal()
      }
    }

    // 未登入又想進入受保護頁 → 導向登入
    if (!isPublic && !auth.me) {
      return next('/login')
    }

    // 已登入又想進登入或註冊頁 → 導向首頁
    if (isPublic && auth.me) {
      return next('/')
    }

    next()
  })
}
