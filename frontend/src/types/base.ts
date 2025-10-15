// src/types/base.ts

/** 後端的標準分頁回應格式 */
export type Paginated<T> = {
  count: number
  next?: string | null
  previous?: string | null
  results: T[]
}

/** 通用的後端回應錯誤 */
export type ApiError = {
  detail?: string
  [key: string]: unknown
}

/** 通用時間戳格式（ISO 字串） */
export type Timestamp = string

/** 別名：方便語義化使用 */
export type ISODateString = Timestamp