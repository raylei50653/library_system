export type Loan = {
  id: number
  book: {
    id: number
    title: string
    author?: string
  }
  borrowed_at: string      // ISO
  due_at: string           // ISO
  returned_at?: string     // ISO | null
  renewable?: boolean
}
