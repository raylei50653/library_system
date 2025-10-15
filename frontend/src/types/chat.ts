// src/types/chat.ts
export type TicketStatus = 'open' | 'closed'

export type Ticket = {
  id: number
  subject: string
  status: TicketStatus
  user_id: number
  assignee_id?: number | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: number
  ticket_id: number
  content: string
  is_ai: boolean
  created_at: string
  user_id?: number | null
  response_meta?: Record<string, unknown> | null
}

// 如果你的專案還沒有共用分頁型別，先用這個簡版：
// export type Paginated<T> = { count: number; next?: string | null; previous?: string | null; results: T[] }
