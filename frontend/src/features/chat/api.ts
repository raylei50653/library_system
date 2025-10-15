// src/features/chat/api.ts
import { http } from '@/lib/http'

/** ---------------- Types ---------------- */

export type Paginated<T> = {
  count: number
  results: T[]
  next?: string | null
  previous?: string | null
}

export type TicketStatus = 'open' | 'closed'

export type Ticket = {
  id: number
  subject: string
  status: TicketStatus
  config?: Record<string, unknown> | null
  assignee?: number | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: number
  ticket: number
  content: string
  is_ai: boolean
  created_at: string
  response_meta?: Record<string, unknown> | null
}

/** 小工具：統一把 boolean 轉 'true' | 'false'（避免不同頁面各自轉） */
function toBoolString(v: boolean | string | undefined): string | undefined {
  if (v === undefined) return undefined
  if (typeof v === 'string') return v
  return v ? 'true' : 'false'
}

/** ---------------- Tickets ---------------- */

/** 取得票單列表（後端支援 mine/status/page/page_size） */
export async function listTickets(
  params: { mine?: boolean | string; status?: string; page?: number; page_size?: number } = {},
  opts?: { signal?: AbortSignal },
): Promise<Paginated<Ticket>> {
  const { data } = await http.get<Paginated<Ticket>>('/chat/tickets/', {
    params: {
      mine: toBoolString(params.mine),
      status: params.status,
      page: params.page ?? 1,
      page_size: params.page_size ?? 10,
    },
    signal: opts?.signal,
  })
  return data
}

/** 建立票單：後端可能回 { ticket_id } 或 { id } → 統一回傳 number */
export async function createTicket(
  input: { subject: string; content?: string; config?: Record<string, unknown> },
): Promise<number> {
  const { data } = await http.post<{ ticket_id?: number; id?: number }>('/chat/tickets/', {
    subject: input.subject,
    content: input.content,
    config: input.config,
  })
  const id = data.id ?? data.ticket_id
  if (typeof id !== 'number') {
    // 這樣的錯誤訊息在 Sentry / console 都很好追
    throw new Error('Unexpected createTicket response: missing id/ticket_id')
  }
  return id
}

/** ---------------- Messages ---------------- */

export async function listMessages(
  ticketId: number,
  page = 1,
  pageSize = 100,
  opts?: { signal?: AbortSignal },
): Promise<Paginated<Message>> {
  const { data } = await http.get<Paginated<Message>>('/chat/messages/', {
    params: { ticket_id: ticketId, page, page_size: pageSize },
    signal: opts?.signal,
  })
  return data
}

export async function postMessage(ticketId: number, content: string): Promise<Message> {
  const { data } = await http.post<Message>('/chat/messages/', { ticket_id: ticketId, content })
  return data
}

/** ---------------- AI ---------------- */

/** 單次 AI 回覆（同步）：POST /chat/ai/reply/ */
export async function aiReply(
  ticketId: number,
  content: string,
): Promise<{ message_id: number; content: string }> {
  const { data } = await http.post<{ message_id: number; content: string }>(
    '/chat/ai/reply/',
    { ticket_id: ticketId, content },
  )
  return data
}
