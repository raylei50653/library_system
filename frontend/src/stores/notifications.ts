// src/stores/notifications.ts
import { defineStore } from 'pinia'
import { fetchUnreadCount } from '@/features/notifications/api'

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    unread: 0 as number,
    _pollTimer: undefined as number | undefined,
    _pollIntervalMs: 30000 as number,
    _firstLoaded: false as boolean,
  }),
  getters: {
    hasUnread: (s) => s.unread > 0,
    firstLoaded: (s) => s._firstLoaded,
  },
  actions: {
    async refreshUnread() {
      try {
        const n = await fetchUnreadCount()
        this.unread = n
      } catch {
        // 401 或其它錯誤時，保持現值；若想遇錯清零，可改為：this.unread = 0
      } finally {
        this._firstLoaded = true
      }
    },
    ensurePolling(intervalMs?: number) {
      if (intervalMs) this._pollIntervalMs = intervalMs
      if (this._pollTimer) return
      // 先跑一次
      this.refreshUnread()
      this._pollTimer = window.setInterval(() => this.refreshUnread(), this._pollIntervalMs)
    },
    stopPolling() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer)
        this._pollTimer = undefined
      }
    },
    /** 在頁面操作「全部已讀」後，可直接同步到 badge */
    setZero() {
      this.unread = 0
    },
    /** 單筆已讀後，同步遞減（保底不負數） */
    dec() {
      this.unread = Math.max(0, this.unread - 1)
    },
  },
})
