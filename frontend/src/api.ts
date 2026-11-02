export interface HealthResponse {
  status: 'ok'
  service: string
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/health`, { signal })
  if (!response.ok) throw new Error(`API returned HTTP ${response.status}`)
  const data: unknown = await response.json()
  if (
    typeof data !== 'object' || data === null ||
    !('status' in data) || data.status !== 'ok' ||
    !('service' in data) || typeof data.service !== 'string'
  ) throw new Error('Unexpected API response')
  return { status: data.status, service: data.service }
}
