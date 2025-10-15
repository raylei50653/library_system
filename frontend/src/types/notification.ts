// src/types/notification.ts
import type { Timestamp } from './base'

/** 對應後端 Notification 基本欄位（其餘欄位以可選保守處理） */
export type Notification = {
  id: number
  /** 簡短標題（如「續借成功」、「書籍到期提醒」） */
  title: string
  /** 內文可能命名為 body 或 message，這邊兩者皆備 */
  body?: string | null
  message?: string | null
  /** 是否已讀 */
  is_read: boolean
  /** 建立時間（ISO 字串） */
  created_at: Timestamp
  /** 可選關聯（例如 Loan ID） */
  loan?: number | null
  loan_id?: number | null
  /** 後端可能額外附帶之任意欄位 */
  [key: string]: unknown
}
