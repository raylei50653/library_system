// src/features/auth/api.ts
import { http } from '@/lib/http'

export type Me = { id: number; email: string; display_name?: string }

export type LoginResponse = {
  access_token?: string
  refresh_token?: string
  access?: string
  refresh?: string
  token_type?: string
}

export async function apiLogin(email: string, password: string) {
  return http.post<LoginResponse>(`/auth/login/`, { email, password })
}

export async function apiRegister(payload: { email: string; password: string; display_name?: string }) {
  return http.post(`/auth/register/`, payload)
}

export async function apiMe() {
  return http.get<Me>(`/auth/me/`)
}
