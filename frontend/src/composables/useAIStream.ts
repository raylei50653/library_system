// src/composables/useAIStream.ts
import { ref, onBeforeUnmount } from 'vue'
import { env } from '@/config/env'
import { storage } from '@/lib/storage'

type StartArgs = {
  ticketId: number
  content: string
  onDelta: (chunk: string) => void        // 每次收到一段 token
  onOpen?: () => void
  onDone?: () => void
}

function joinUrl(base: string, path: string) {
  if (base.endsWith('/')) base = base.slice(0, -1)
  return `${base}${path.startsWith('/') ? '' : '/'}${path}`
}

export function useAIStream() {
  const isActive = ref(false)
  const error = ref<Error | null>(null)
  let controller: AbortController | null = null

  async function start({ ticketId, content, onDelta, onOpen, onDone }: StartArgs) {
    stop()
    error.value = null
    controller = new AbortController()
    isActive.value = true

    const base = env.SSE_BASE || env.API_BASE
    const url = joinUrl(
      base,
      `/chat/ai/stream/?ticket_id=${encodeURIComponent(String(ticketId))}&content=${encodeURIComponent(content)}`
    )
    const token = storage.get('access')

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        signal: controller.signal,
      })

      // 針對常見權限錯誤快速失敗
      if (res.status === 401 || res.status === 403) {
        throw new Error(`SSE unauthorized: HTTP ${res.status}`)
      }
      if (!res.ok || !res.body) {
        throw new Error(`SSE HTTP ${res.status}`)
      }

      onOpen?.()

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // 依規範：一個事件可包含多行 data:，要以 \n 合併
      const processChunk = (text: string) => {
        buffer += text
        // 以空行分隔事件；支援 \r\n
        const events = buffer.split(/\r?\n\r?\n/)
        buffer = events.pop() || '' // 留下未完整事件的殘段

        for (const rawEvt of events) {
          // 忽略心跳（以冒號開頭）
          const lines = rawEvt.split(/\r?\n/).filter(l => l.trim() !== '' && !l.startsWith(':'))
          if (!lines.length) continue

          let dataLines: string[] = []
          for (const line of lines) {
            // 只關心 data:，其他如 id:/event:/retry: 可按需擴充
            if (line.startsWith('data:')) {
              dataLines.push(line.slice(5).trimStart())
            }
          }

          if (!dataLines.length) continue
          const payload = dataLines.join('\n')

          if (payload === '[DONE]') {
            isActive.value = false
            onDone?.()
            return 'DONE' as const
          }
          onDelta(payload)
        }
        return 'CONTINUE' as const
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value, { stream: true })
        const state = processChunk(text)
        if (state === 'DONE') return
      }

      // 讀取結束後做一次 flush，避免殘留資料沒被處理
      const rest = decoder.decode()
      if (rest) {
        const state = processChunk(rest)
        if (state === 'DONE') return
      }

      isActive.value = false
      onDone?.()
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        error.value = e instanceof Error ? e : new Error(String(e))
      }
    } finally {
      isActive.value = false
    }
  }

  function stop() {
    if (controller) controller.abort()
    controller = null
    isActive.value = false
  }

  onBeforeUnmount(stop)
  return { isActive, error, start, stop }
}
