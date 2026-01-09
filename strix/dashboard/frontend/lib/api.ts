import type { DashboardState, HistoricalData } from '@/types'

// API base URL - defaults to current origin for same-origin API calls
const API_BASE = typeof window !== 'undefined' ? window.location.origin : ''

/**
 * Fetch dashboard state from the API
 */
export async function fetchDashboardState(): Promise<DashboardState | null> {
  try {
    const response = await fetch(`${API_BASE}/api/state`)
    if (!response.ok) {
      throw new Error(`Failed to fetch state: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Error fetching dashboard state:', error)
    return null
  }
}

/**
 * Fetch historical data for charts
 * @param metric - The metric type to fetch (tokens, cost, rate, etc.)
 * @param duration - Duration in seconds to fetch history for
 */
export async function fetchHistory(
  metric: string,
  duration: number = 3600
): Promise<HistoricalData[]> {
  try {
    const response = await fetch(
      `${API_BASE}/api/history?metric=${encodeURIComponent(metric)}&duration=${duration}`
    )
    if (!response.ok) {
      throw new Error(`Failed to fetch history: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Error fetching history:', error)
    return []
  }
}

/**
 * Export dashboard data in specified format
 * @param format - Export format ('json' or 'csv')
 */
export async function exportData(format: 'json' | 'csv'): Promise<Blob> {
  try {
    const response = await fetch(`${API_BASE}/api/export?format=${format}`)
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`)
    }
    return await response.blob()
  } catch (error) {
    console.error('Error exporting data:', error)
    throw error
  }
}

/**
 * Download a blob as a file
 * @param blob - The blob to download
 * @param filename - The filename to save as
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Subscribe to real-time updates via Server-Sent Events
 * @param onUpdate - Callback function for state updates
 * @returns Cleanup function to close the connection
 */
export function subscribeToUpdates(
  onUpdate: (state: Partial<DashboardState>) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/api/events`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onUpdate(data)
    } catch (error) {
      console.error('Error parsing SSE data:', error)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error)
  }

  return () => {
    eventSource.close()
  }
}
