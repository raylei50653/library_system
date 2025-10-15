import { http } from '@/lib/http'

/** 後端回傳的收藏項（簡化只取 book.id） */
type FavoriteItem = { id: number; book: { id: number } }

/** 極簡快取，避免列表上每張卡片都打 API */
let cacheLoaded = false
let favIds = new Set<number>()

export async function getFavorites() {
  const { data } = await http.get<FavoriteItem[]>(`/api/me/favorites/`)
  return data
}

export async function loadFavoritesOnce(): Promise<Set<number>> {
  if (!cacheLoaded) {
    try {
      const list = await getFavorites()
      favIds = new Set(list.map((f) => f.book.id))
    } finally {
      cacheLoaded = true
    }
  }
  return favIds
}

export async function isFavorite(bookId: number) {
  const ids = await loadFavoritesOnce()
  return ids.has(bookId)
}

export async function addFavorite(bookId: number) {
  await http.post(`/api/me/favorites/${bookId}/`)
  favIds.add(bookId) // 後端冪等，直接同步到快取
}

export async function removeFavorite(bookId: number) {
  await http.delete(`/api/me/favorites/${bookId}/`)
  favIds.delete(bookId) // 同步快取
}

/** 若在其他地方異動了收藏清單，可手動失效快取 */
export function invalidateFavorites() {
  cacheLoaded = false
  favIds.clear()
}
