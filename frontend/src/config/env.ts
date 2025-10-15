export const env = {
  API_BASE: import.meta.env.VITE_API_BASE,
  SSE_BASE: import.meta.env.VITE_SSE_BASE || import.meta.env.VITE_API_BASE,
  ENABLE_SIGNUP: String(import.meta.env.VITE_ENABLE_SIGNUP ?? 'true') === 'true',
} as const
