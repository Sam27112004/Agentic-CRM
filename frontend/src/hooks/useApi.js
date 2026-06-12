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
      if (filters.requires_human) params.set('requires_human', 'true')
      if (filters.search) params.set('search', filters.search)
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

  const fetchStats = useCallback(() => {
    setLoading(true)
    fetch(`${API_BASE}/dashboard/stats`)
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return { stats, loading, refetchStats: fetchStats }
}

export function useThread(contactEmail) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchThread = useCallback(() => {
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

  useEffect(() => {
    fetchThread()
  }, [fetchThread])

  return { data, loading, error, refetch: fetchThread }
}

export async function approveDraft(draftId) {
  const res = await fetch(`${API_BASE}/drafts/${draftId}/approve`, { method: 'POST' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function editDraft(draftId, content) {
  const res = await fetch(`${API_BASE}/drafts/${draftId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function sendResponse(emailId, content) {
  const res = await fetch(`${API_BASE}/respond/${emailId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function useSentimentTrend(sender = null, days = 30) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let url = `${API_BASE}/analytics/sentiment-trend?days=${days}`
    if (sender) url += `&sender=${encodeURIComponent(sender)}`
    
    fetch(url)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [sender, days])

  return { data, loading }
}

export function useReputation(companyName) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!companyName) {
      setLoading(false)
      return
    }
    fetch(`${API_BASE}/intelligence/reputation?company_name=${encodeURIComponent(companyName)}`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [companyName])

  return { data, loading }
}


export function useAtRiskAccounts() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/analytics/at-risk-accounts`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export function useAgentMetrics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/analytics/agent-metrics`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export function useResponseHeatmap() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/analytics/response-heatmap`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export async function updateEmail(emailId, payload) {
  const res = await fetch(`${API_BASE}/api/emails/${emailId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    throw new Error('Failed to update email')
  }
  return res.json()
}

export function useRagSearch(query) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!query) {
      setLoading(false)
      return
    }
    fetch(`${API_BASE}/rag/search?q=${encodeURIComponent(query)}`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [query])

  return { data, loading }
}
