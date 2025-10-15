export type Book = {
  id: number
  title: string
  author?: string
  category?: string
  status?: 'available' | 'unavailable'
  available_count?: number
}
