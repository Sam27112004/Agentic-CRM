import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line
} from 'recharts'
import { useDashboardStats, useSentimentTrend } from '../hooks/useApi.js'

/* ------------------------------------------------------------------ */
/* Color Maps                                                          */
/* ------------------------------------------------------------------ */

const CATEGORY_COLORS = {
  Complaint: '#ef4444',     // red-500
  Legal: '#b91c1c',         // red-700
  Security: '#b91c1c',      // red-700
  Billing: '#f59e0b',       // amber-500
  'Bug Report': '#f97316',  // orange-500
  Compliance: '#a855f7',    // purple-500
  Inquiry: '#3b82f6',       // blue-500
  'Feature Request': '#14b8a6', // teal-500
  Spam: '#64748b',          // slate-500
  Internal: '#64748b',      // slate-500
  Pending: '#eab308',       // yellow-500
  Other: '#64748b',         // slate-500
}

const STATUS_COLORS = {
  Received: '#3b82f6',      // blue-500
  Processing: '#eab308',    // yellow-500
  Replied: '#22c55e',       // green-500
  Escalated: '#ef4444',     // red-500
  Ignored: '#64748b',       // slate-500
}

/* ------------------------------------------------------------------ */
/* Custom Tooltips                                                     */
/* ------------------------------------------------------------------ */

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-900/90 p-3 shadow-xl backdrop-blur-sm">
        <p className="mb-1 font-medium text-slate-200">{label || payload[0].name}</p>
        <p className="text-sm font-bold text-indigo-400">
          {payload[0].value} email{payload[0].value !== 1 ? 's' : ''}
        </p>
      </div>
    )
  }
  return null
}

/* ------------------------------------------------------------------ */
/* Analytics Page                                                      */
/* ------------------------------------------------------------------ */

export default function Analytics() {
  const { stats, loading } = useDashboardStats()
  const { data: sentimentData, loading: sentimentLoading } = useSentimentTrend()

  // Format data for Recharts
  const categoryData = useMemo(() => {
    if (!stats?.by_category) return []
    return Object.entries(stats.by_category)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [stats])

  const statusData = useMemo(() => {
    if (!stats?.by_status) return []
    return Object.entries(stats.by_status)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [stats])

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-slate-500">Loading analytics...</p>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-red-400">Failed to load analytics data.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-3xl font-black text-white tracking-tight">Analytics <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Dashboard</span></h2>
        <p className="text-slate-400 mt-2 text-lg">Overview of email triage volume and classification</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-transform hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(79,70,229,0.15)] group">
          <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-slate-500 group-hover:text-slate-300 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Total Ingested
          </p>
          <p className="text-5xl font-black text-white">{stats.total_emails}</p>
        </div>
        
        <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-transform hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(79,70,229,0.3)] relative overflow-hidden group">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-indigo-500/20 blur-3xl group-hover:bg-indigo-500/30 transition-colors"></div>
          <p className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-3 relative z-10 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Automated Replies
          </p>
          <p className="text-5xl font-black text-white relative z-10">{stats.by_status?.Replied || 0}</p>
        </div>
        
        <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-transform hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(239,68,68,0.3)] relative overflow-hidden group">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-red-500/20 blur-3xl group-hover:bg-red-500/30 transition-colors"></div>
          <p className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-3 relative z-10 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Human Escalation
          </p>
          <p className="text-5xl font-black text-white relative z-10">{stats.by_status?.Escalated || 0}</p>
        </div>

        <div className="rounded-2xl border border-yellow-500/30 bg-yellow-950/20 p-6 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-transform hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(234,179,8,0.3)] relative overflow-hidden group">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-yellow-500/20 blur-3xl group-hover:bg-yellow-500/30 transition-colors"></div>
          <p className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-3 relative z-10 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Pending Agent
          </p>
          <p className="text-5xl font-black text-white relative z-10">{stats.by_status?.Processing || 0}</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        
        {/* Category Breakdown (Bar Chart) */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
          <h3 className="text-lg font-semibold text-white mb-6">Volume by Category</h3>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  tick={{ fill: '#cbd5e1' }}
                  width={100}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.name] || CATEGORY_COLORS.Other} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Status Distribution (Pie Chart) */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
          <h3 className="text-lg font-semibold text-white mb-6">Current Status Distribution</h3>
          <div className="h-80 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={120}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={STATUS_COLORS[entry.name] || STATUS_COLORS.Ignored} stroke="rgba(0,0,0,0)" />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom" 
                  height={36} 
                  iconType="circle"
                  formatter={(value) => <span className="text-slate-300 ml-1">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Sentiment Trend Chart */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 mt-6">
        <h3 className="text-lg font-semibold text-white mb-6">Sentiment Trend (30 Days)</h3>
        <div className="h-80 w-full">
          {sentimentLoading ? (
            <div className="flex h-full items-center justify-center text-slate-500">Loading trend data...</div>
          ) : sentimentData && sentimentData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sentimentData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickFormatter={(tick) => new Date(tick).toLocaleDateString()} />
                <YAxis domain={[-1, 1]} stroke="#94a3b8" fontSize={12} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line type="monotone" dataKey="avg_sentiment" name="Average Sentiment" stroke="#8b5cf6" activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-slate-500">No sentiment data available</div>
          )}
        </div>
      </div>
    </div>
  )
}
