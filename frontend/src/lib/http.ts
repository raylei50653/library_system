// src/lib/http.ts
import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { env } from '@/config/env'
import { storage } from './storage'

type RefreshResp = { access: string }

export const http: AxiosInstance = axios.create({
  baseURL: env.API_BASE, // 例: http://127.0.0.1:8000
  withCredentials: false,
  headers: { 'Content-Type': 'application/json' },
})

// ---- Request 攔截：帶上 Access Token ----
http.interceptors.request.use((config) => {
  const token = storage.get('access')
  if (token) {
    config.headers = config.headers || {}
    ;(config.headers as any).Authorization = `Bearer ${token}`
  }
  return config
})

// ---- Refresh Token 機制 ----
let isRefreshing = false
let queue: Array<(token: string | null) => void> = []

function runQueue(token: string | null) {
  queue.forEach((cb) => cb(token))
  queue = []
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = storage.get('refresh')
  if (!refresh) return null
  try {
    const { data } = await axios.post<RefreshResp>(
      `${env.API_BASE}/auth/refresh/`,
      { refresh },
      { headers: { 'Content-Type': 'application/json' } },
    )
    storage.set('access', data.access)
    return data.access
  } catch {
    storage.remove('access')
    storage.remove('refresh')
    return null
  }
}

// ---- Response 攔截：自動刷新 Access Token ----
http.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    if (!original) return Promise.reject(err)
    const status = err.response?.status

    // 忽略認證端點
    const isAuthEndpoint =
      original.url?.includes('/auth/login') ||
      original.url?.includes('/auth/register') ||
      original.url?.includes('/auth/refresh')

    if (status === 401 && !isAuthEndpoint && !original._retry) {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push((token) => {
            if (!token) reject(err)
            else {
              original.headers = original.headers || {}
              ;(original.headers as any).Authorization = `Bearer ${token}`
              resolve(http(original))
            }
          })
        })
      }

      isRefreshing = true
      const newToken = await refreshAccessToken()
      isRefreshing = false
      runQueue(newToken)

      if (newToken) {
        original.headers = original.headers || {}
        ;(original.headers as any).Authorization = `Bearer ${newToken}`
        return http(original)
      }
    }

    return Promise.reject(err)
  },
)
