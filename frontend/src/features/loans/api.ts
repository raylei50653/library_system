import { http } from '@/lib/http'
import type { Loan } from '@/types/loan'

export async function listMyLoans(params?: { page?: number; page_size?: number }) {
  const { data } = await http.get<{ count: number; results: Loan[] }>(`/api/loans/`, { params })
  return data
}

export async function borrowBook(bookId: number) {
  // 後端約定：有庫存 → 建立一筆借閱
  const { data } = await http.post<Loan>(`/api/loans/`, { book_id: bookId })
  return data
}

export async function returnLoan(loanId: number) {
  const { data } = await http.post<Loan>(`/api/loans/${loanId}/return/`)
  return data
}

export async function renewLoan(loanId: number) {
  const { data } = await http.post<Loan>(`/api/loans/${loanId}/renew/`)
  return data
}

// 若無庫存 → 走預約（候補）
export async function reserveBook(bookId: number) {
  const { data } = await http.post<{ id: number; book_id: number; status: 'queued' | 'ready' }>(
    `/api/reservations/`,
    { book_id: bookId },
  )
  return data
}
