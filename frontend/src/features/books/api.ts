import { http } from '@/lib/http'
import type { Book } from '@/types/book'

export type ListBooksParams = {
  page?: number
  page_size?: number
  query?: string
  category?: string
}

export async function listBooks(params?: ListBooksParams) {
  const { data } = await http.get<{ count: number; results: Book[] }>(`/api/books/`, { params })
  return data
}

export async function getBook(id: number) {
  const { data } = await http.get<Book>(`/api/books/${id}/`)
  return data
}
