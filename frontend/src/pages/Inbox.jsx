import { useState, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table'
import { useEmails, useDashboardStats } from '../hooks/useApi.js'

/* ------------------------------------------------------------------ */
/* Badge helpers                                                       */
/* ------------------------------------------------------------------ */

const CATEGORY_COLORS = {
  Complaint: 'bg-red-500/20 text-red-300',
  Legal: 'bg-red-700/20 text-red-200',
  Security: 'bg-red-700/20 text-red-200',
  Billing: 'bg-amber-500/20 text-amber-300',
  'Bug Report': 'bg-orange-500/20 text-orange-300',
  Compliance: 'bg-purple-500/20 text-purple-300',
  Inquiry: 'bg-blue-500/20 text-blue-300',
  'Feature Request': 'bg-teal-500/20 text-teal-300',
  Spam: 'bg-slate-600/30 text-slate-400',
  Internal: 'bg-slate-600/30 text-slate-400',
  Pending: 'bg-yellow-500/20 text-yellow-300',
  Other: 'bg-slate-600/30 text-slate-400',
}

const URGENCY_COLORS = {
  Critical: 'bg-red-600/20 text-red-300 ring-1 ring-red-500/40',
  High: 'bg-orange-500/20 text-orange-300',
  Medium: 'bg-yellow-500/20 text-yellow-300',
  Low: 'bg-green-500/20 text-green-300',
}

const STATUS_COLORS = {
  Received: 'bg-blue-500/20 text-blue-300',
  Processing: 'bg-yellow-500/20 text-yellow-300',
  Replied: 'bg-green-500/20 text-green-300',
  Escalated: 'bg-red-500/20 text-red-300',
  Ignored: 'bg-slate-600/30 text-slate-400',
}

function Badge({ label, colorMap }) {
  const cls = colorMap[label] || 'bg-slate-600/30 text-slate-400'
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label || '—'}
    </span>
  )
}

function SentimentDot({ score }) {
  if (score === null || score === undefined) return <span className="text-slate-600">—</span>
  const numScore = Number(score);
  const color = numScore > 0.2 ? 'text-green-400' : numScore < -0.2 ? 'text-red-400' : 'text-yellow-400'
  return <span className={`font-mono text-sm ${color}`}>{numScore.toFixed(2)}</span>
}

/* ------------------------------------------------------------------ */
/* Filter tabs                                                         */
/* ------------------------------------------------------------------ */

const STATUS_TABS = [
  { key: null, label: 'All' },
  { key: 'NeedsHuman', label: 'Needs Human' },
  { key: 'Received', label: 'Pending' },
  { key: 'Escalated', label: 'Escalated' },
  { key: 'Replied', label: 'Replied' },
  { key: 'Ignored', label: 'Spam' },
]

/* ------------------------------------------------------------------ */
/* Columns                                                             */
/* ------------------------------------------------------------------ */

function buildColumns(onSelectThread) {
  return [
    {
      accessorKey: 'sender',
      header: 'Sender',
      cell: ({ getValue }) => (
        <span className="font-medium text-slate-100 truncate max-w-[200px] block">
          {getValue()}
        </span>
      ),
    },
    {
      accessorKey: 'subject',
      header: 'Subject',
      cell: ({ getValue }) => (
        <span className="truncate max-w-[280px] block text-slate-300">{getValue()}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ getValue }) => <Badge label={getValue()} colorMap={STATUS_COLORS} />,
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ getValue }) => <Badge label={getValue()} colorMap={CATEGORY_COLORS} />,
    },
    {
      accessorKey: 'urgency',
      header: 'Urgency',
      cell: ({ getValue }) => <Badge label={getValue()} colorMap={URGENCY_COLORS} />,
    },
    {
      accessorKey: 'sentiment_score',
      header: 'Sentiment',
      cell: ({ getValue }) => <SentimentDot score={getValue()} />,
    },
    {
      accessorKey: 'timestamp',
      header: 'Time',
      cell: ({ getValue }) => {
        const v = getValue()
        if (!v) return '—'
        try {
          return new Date(v).toLocaleString('en-US', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
          })
        } catch {
          return v
        }
      },
    },
  ]
}

/* ------------------------------------------------------------------ */
/* Stats bar                                                           */
/* ------------------------------------------------------------------ */

function StatsBar({ stats }) {
  if (!stats) return null
  const items = [
    { label: 'Total Ingested', value: stats.total_emails, color: 'text-white', glow: 'shadow-[0_0_15px_rgba(255,255,255,0.1)]' },
    { label: 'Pending Triage', value: stats.by_status?.Received || 0, color: 'text-indigo-400', glow: 'shadow-[0_0_15px_rgba(129,140,248,0.2)]' },
    { label: 'Needs Escalation', value: stats.by_status?.Escalated || 0, color: 'text-red-400', glow: 'shadow-[0_0_15px_rgba(248,113,113,0.2)]' },
    { label: 'Replied', value: stats.by_status?.Replied || 0, color: 'text-emerald-400', glow: 'shadow-[0_0_15px_rgba(52,211,153,0.2)]' },
    { label: 'Spam / Ignored', value: stats.by_status?.Ignored || 0, color: 'text-slate-400', glow: 'shadow-[0_0_15px_rgba(148,163,184,0.1)]' },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
      {items.map((s) => (
        <div key={s.label} className={`relative overflow-hidden rounded-xl border border-slate-700/50 bg-slate-900/40 p-5 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-slate-600/50 hover:bg-slate-800/50 ${s.glow}`}>
          <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-white/5 blur-2xl"></div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-1 relative z-10">{s.label}</p>
          <p className={`text-3xl font-black ${s.color} relative z-10`}>{s.value}</p>
        </div>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Inbox page                                                          */
/* ------------------------------------------------------------------ */

export default function Inbox({ onSelectThread }) {
  const [statusFilter, setStatusFilter] = useState(null)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [sorting, setSorting] = useState([{ id: 'timestamp', desc: true }])

  const activeFilters = useMemo(() => {
    let filters = { sort_by: sorting[0].id, sort_dir: sorting[0].desc ? 'desc' : 'asc', page, page_size: 50, category: categoryFilter || undefined }
    if (statusFilter === 'NeedsHuman') {
      filters.requires_human = true
    } else if (statusFilter) {
      filters.status = statusFilter
    }
    if (searchQuery) filters.search = searchQuery
    return filters
  }, [statusFilter, categoryFilter, searchQuery, sorting, page])

  const { emails, total, loading, error, refetch } = useEmails(activeFilters)
  const { stats, refetchStats } = useDashboardStats()

  const handleRefresh = () => {
    refetch()
    refetchStats()
  }

  const columns = useMemo(() => buildColumns(onSelectThread), [onSelectThread])

  const table = useReactTable({
    data: emails || [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,
  })

  const totalPages = Math.ceil((total || 0) / 50)

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
            Mission <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Control</span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">Real-time email triage and automated response monitoring.</p>
        </div>
        <button
          onClick={handleRefresh}
          className="rounded-lg bg-indigo-600/20 ring-1 ring-indigo-500/50 px-4 py-2 text-sm font-semibold text-indigo-300 hover:bg-indigo-600 hover:text-white transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)] flex items-center gap-2 group"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 group-hover:rotate-180 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Data
        </button>
      </div>

      <StatsBar stats={stats} />

      {/* Filters row */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-6 bg-slate-900/30 p-4 rounded-xl border border-slate-800/60 backdrop-blur-sm shadow-sm">
        {/* Status tabs */}
        <div className="flex flex-wrap gap-2">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.label}
              onClick={() => { setStatusFilter(tab.key); setPage(1) }}
              className={`rounded-full px-5 py-2 text-sm font-semibold transition-all duration-300 ${
                statusFilter === tab.key
                  ? 'bg-indigo-600 text-white shadow-[0_4px_15px_rgba(79,70,229,0.4)]'
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
            className="w-full sm:w-auto rounded-lg border border-slate-700/50 bg-slate-800/80 px-4 py-2.5 text-sm font-medium text-slate-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all shadow-inner"
          >
            <option value="">All Categories</option>
            {['Complaint', 'Inquiry', 'Bug Report', 'Feature Request', 'Compliance', 'Legal', 'Billing', 'Spam', 'Internal', 'Pending', 'Security', 'Other'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          {/* Sender search */}
          <div className="relative w-full sm:w-auto">
            <svg xmlns="http://www.w3.org/2000/svg" className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search emails..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
              className="w-full sm:w-64 rounded-lg border border-slate-700/50 bg-slate-800/80 pl-10 pr-4 py-2.5 text-sm font-medium text-slate-300 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all shadow-inner"
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-red-900/30 border border-red-700 px-4 py-2 text-sm text-red-300">
          Error loading emails: {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/60 bg-slate-900/50 backdrop-blur-sm shadow-[0_8px_30px_rgb(0,0,0,0.4)]">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-slate-800/60 bg-slate-900/90 backdrop-blur-md shadow-sm">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="cursor-pointer px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200 select-none"
                  >
                    <span className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' ↑', desc: ' ↓' }[header.column.getIsSorted()] ?? ''}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-slate-500">
                  Loading...
                </td>
              </tr>
            ) : (emails || []).length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-slate-500">
                  No emails found
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => onSelectThread?.(row.original.sender)}
                  className="group cursor-pointer border-b border-slate-800/50 transition-all duration-200 hover:bg-indigo-900/10 hover:shadow-[inset_0_1px_0_0_rgba(99,102,241,0.1),inset_0_-1px_0_0_rgba(99,102,241,0.1)]"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 transition-colors group-hover:text-slate-100">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-slate-400">
          <span>
            Page {page} of {totalPages} ({total} total)
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-30 hover:bg-slate-800"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border border-slate-700 px-3 py-1 disabled:opacity-30 hover:bg-slate-800"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
