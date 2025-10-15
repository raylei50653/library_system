// src/features/notifications/api.ts
import { http } from '@/lib/http'
import type { Paginated } from '@/types/base'
import type { Notification } from '@/types/notification'

export type ListQuery = {
  page?: number
  is_read?: boolean
}

type ListResponse = Paginated<Notification> | Notification[]

function normalizeListResponse(data: ListResponse): Paginated<Notification> {
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data,
    }
  }

  const results = Array.isArray(data.results) ? data.results : []
  return {
    count: typeof data.count === 'number' ? data.count : results.length,
    next: data.next ?? null,
    previous: data.previous ?? null,
    results,
  }
}

/** 取得通知列表（可選 is_read 篩選） */
export async function listNotifications(params: ListQuery = {}) {
  const { data } = await http.get<ListResponse>('/api/me/notifications/', { params })
  return normalizeListResponse(data)
}

/** 單筆標記為已讀 */
export async function markNotificationRead(id: number) {
  await http.post(`/api/me/notifications/${id}/read/`)
}

/** 一次標記所有未讀為已讀 */
export async function markAllNotificationsRead() {
  await http.post('/api/me/notifications/read-all/')
}

/**
 * 取得未讀數：用 is_read=false 查詢並利用分頁回傳的 count。
 * 備註：count 與 page_size 無關，但可傳小 page_size 避免傳輸量。
 */
export async function fetchUnreadCount(): Promise<number> {
  const { data } = await http.get<Paginated<Notification>>('/api/me/notifications/', {
    params: { is_read: false, page_size: 1 },
  })
  return data.count ?? 0
}
