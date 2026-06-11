import { useState, useEffect } from 'react'
import Inbox from './pages/Inbox.jsx'
import ThreadWorkspace from './pages/ThreadWorkspace.jsx'
import Analytics from './pages/Analytics.jsx'

const NAV_ITEMS = [
  { key: 'inbox', label: 'Inbox' },
  { key: 'analytics', label: 'Analytics' },
]

export default function App() {
  const [page, setPage] = useState('inbox')
  const [selectedThread, setSelectedThread] = useState(null)

  // Simple hash-based routing
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.slice(1)
      if (hash.startsWith('thread/')) {
        setSelectedThread(hash.replace('thread/', ''))
        setPage('thread')
      } else if (hash === 'analytics') {
        setPage('analytics')
        setSelectedThread(null)
      } else {
        setPage('inbox')
        setSelectedThread(null)
      }
    }
    handleHash()
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [])

  const navigate = (target) => {
    window.location.hash = target
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Top Nav */}
      <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-screen-2xl items-center gap-6 px-6">
          <h1
            className="cursor-pointer text-lg font-bold tracking-tight text-white"
            onClick={() => navigate('inbox')}
          >
            Agentic<span className="text-indigo-400">CRM</span>
          </h1>
          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                onClick={() => navigate(item.key === 'inbox' ? 'inbox' : item.key)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  page === item.key
                    ? 'bg-indigo-600/20 text-indigo-300'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-screen-2xl px-6 py-6">
        {page === 'inbox' && <Inbox onSelectThread={(email) => navigate(`thread/${email}`)} />}
        {page === 'thread' && (
          <ThreadWorkspace
            contactEmail={selectedThread}
            onBack={() => navigate('inbox')}
          />
        )}
        {page === 'analytics' && <Analytics />}
      </main>
    </div>
  )
}
