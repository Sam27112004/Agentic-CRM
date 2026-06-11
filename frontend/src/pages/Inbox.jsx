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
  const color = score > 0.2 ? 'text-green-400' : score < -0.2 ? 'text-red-400' : 'text-yellow-400'
  return <span className={`font-mono text-sm ${color}`}>{score.toFixed(2)}</span>
}

/* ------------------------------------------------------------------ */
/* Filter tabs                                                         */
/* ------------------------------------------------------------------ */

const STATUS_TABS = [
  { key: null, label: 'All' },
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
    { label: 'Total', value: stats.total_emails, color: 'text-white' },
    { label: 'Pending', value: stats.by_status?.Received || 0, color: 'text-blue-400' },
    { label: 'Escalated', value: stats.by_status?.Escalated || 0, color: 'text-red-400' },
    { label: 'Replied', value: stats.by_status?.Replied || 0, color: 'text-green-400' },
    { label: 'Spam', value: stats.by_status?.Ignored || 0, color: 'text-slate-500' },
  ]
  return (
    <div className="flex gap-6 mb-6">
      {items.map((s) => (
        <div key={s.label} className="rounded-lg border border-slate-800 bg-slate-900/60 px-5 py-3">
          <p className="text-xs text-slate-400 uppercase tracking-wider">{s.label}</p>
          <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
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
  const [senderSearch, setSenderSearch] = useState('')
  const [page, setPage] = useState(1)
  const [sorting, setSorting] = useState([{ id: 'timestamp', desc: true }])

  const filters = useMemo(() => ({
    status: statusFilter,
    category: categoryFilter || undefined,
    sender: senderSearch || undefined,
    sort_by: sorting[0]?.id || 'timestamp',
    sort_dir: sorting[0]?.desc ? 'desc' : 'asc',
    page,
    page_size: 50,
  }), [statusFilter, categoryFilter, senderSearch, sorting, page])

  const { emails, total, loading, error, refetch } = useEmails(filters)
  const { stats } = useDashboardStats()

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
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Mission Control</h2>
        <button
          onClick={refetch}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
        >
          Refresh
        </button>
      </div>

      <StatsBar stats={stats} />

      {/* Filters row */}
      <div className="flex items-center gap-4 mb-4">
        {/* Status tabs */}
        <div className="flex gap-1 rounded-lg bg-slate-900 p-1">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.label}
              onClick={() => { setStatusFilter(tab.key); setPage(1) }}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                statusFilter === tab.key
                  ? 'bg-indigo-600/30 text-indigo-300'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Category filter */}
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 focus:border-indigo-500 focus:outline-none"
        >
          <option value="">All Categories</option>
          {['Complaint', 'Inquiry', 'Bug Report', 'Feature Request', 'Compliance', 'Legal', 'Billing', 'Spam', 'Internal', 'Pending', 'Security', 'Other'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        {/* Sender search */}
        <input
          type="text"
          placeholder="Search sender..."
          value={senderSearch}
          onChange={(e) => { setSenderSearch(e.target.value); setPage(1) }}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 placeholder-slate-500 focus:border-indigo-500 focus:outline-none w-52"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-red-900/30 border border-red-700 px-4 py-2 text-sm text-red-300">
          Error loading emails: {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-slate-800 bg-slate-900/60">
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
                  className="cursor-pointer border-b border-slate-800/50 hover:bg-slate-800/40 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3">
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
