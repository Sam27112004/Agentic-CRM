import { useState, useEffect, useCallback } from 'react'

const API_BASE = ''

export function useEmails(filters = {}) {
  const [data, setData] = useState({ emails: [], total: 0, page: 1, page_size: 50 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchEmails = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.category) params.set('category', filters.category)
      if (filters.urgency) params.set('urgency', filters.urgency)
      if (filters.sender) params.set('sender', filters.sender)
      if (filters.sort_by) params.set('sort_by', filters.sort_by)
      if (filters.sort_dir) params.set('sort_dir', filters.sort_dir)
      if (filters.page) params.set('page', String(filters.page))
      if (filters.page_size) params.set('page_size', String(filters.page_size))

      const res = await fetch(`${API_BASE}/api/emails?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => { fetchEmails() }, [fetchEmails])

  return { ...data, loading, error, refetch: fetchEmails }
}

export function useDashboardStats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/dashboard/stats`)
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { stats, loading }
}

export function useThread(contactEmail) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!contactEmail) return
    setLoading(true)
    fetch(`${API_BASE}/threads/${encodeURIComponent(contactEmail)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [contactEmail])

  return { data, loading, error }
}
