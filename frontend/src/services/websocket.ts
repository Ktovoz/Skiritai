import type { WSMessage } from '../types/case'

type MessageHandler = (msg: WSMessage) => void

export function createCaseWS(
  caseId: string,
  onMessage: MessageHandler,
): { close: () => void } {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.host}/api/ws/cases/${caseId}`

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let retries = 0
  const maxRetries = 5
  let closed = false

  function connect() {
    if (closed) return
    ws = new WebSocket(url)

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        onMessage(msg)
      } catch {
        // ignore parse errors
      }
    }

    ws.onopen = () => {
      retries = 0
    }

    ws.onclose = () => {
      if (closed) return
      retries++
      if (retries <= maxRetries) {
        const delay = Math.min(1000 * 2 ** retries, 10000)
        reconnectTimer = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  connect()

  return {
    close() {
      closed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    },
  }
}
