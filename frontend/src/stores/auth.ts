// src/stores/auth.ts
import { defineStore } from 'pinia'
import { http } from '@/lib/http'
import { storage } from '@/lib/storage'

type Me = {
  id: number
  email: string
  display_name?: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    me: null as Me | null,
    loadingMe: false,
  }),

  actions: {
    // 登入
    async login(email: string, password: string) {
      const { data } = await http.post<{
        access_token?: string
        refresh_token?: string
        access?: string
        refresh?: string
      }>(
        '/auth/login/',
        { email, password },
      )

      const accessToken = data.access_token ?? data.access
      const refreshToken = data.refresh_token ?? data.refresh

      if (!accessToken || !refreshToken) {
        throw new Error('登入回應缺少必要的 token 資料')
      }

      storage.set('access', accessToken)
      storage.set('refresh', refreshToken)

      await this.fetchMe()
    },

    // 抓取使用者資料
    async fetchMe() {
      this.loadingMe = true
      try {
        const { data } = await http.get<Me>('/auth/me/')
        this.me = data
      } catch (err) {
        this.me = null
        throw err
      } finally {
        this.loadingMe = false
      }
    },

    // 登出
    async logout() {
      try {
        const refresh = storage.get('refresh')
        if (refresh) await http.post('/auth/logout/', { refresh })
      } catch {
        // ignore
      } finally {
        this.logoutLocal()
      }
    },

    // 清除本地狀態
    logoutLocal() {
      storage.remove('access')
      storage.remove('refresh')
      this.me = null
    },
  },
})
