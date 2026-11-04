const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string, string> = {}) {
    super(message)
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/api${path}`, options)
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    const fields: Record<string, string> = {}
    if (Array.isArray(detail)) {
      for (const item of detail) {
        if (Array.isArray(item.loc) && typeof item.msg === 'string') {
          fields[String(item.loc.at(-1))] = item.msg
        }
      }
    }
    throw new ApiError(response.status,
      typeof detail === 'string' ? detail : response.status === 422
        ? 'Check the highlighted fields.' : `Request failed (HTTP ${response.status}).`, fields)
  }
  return response.json() as Promise<T>
}

export function jsonBody(data: unknown): RequestInit {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }
}
