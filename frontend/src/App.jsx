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
      <header className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/70 backdrop-blur-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
        <div className="mx-auto flex h-16 max-w-screen-2xl items-center gap-8 px-8">
          <div
            className="group flex cursor-pointer items-center gap-2"
            onClick={() => navigate('inbox')}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 shadow-[0_0_15px_rgba(79,70,229,0.5)] transition-transform group-hover:scale-105">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
            </div>
            <h1 className="text-xl font-black tracking-tight text-white transition-opacity group-hover:opacity-90">
              Agentic<span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">CRM</span>
            </h1>
          </div>
          <nav className="flex gap-2">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                onClick={() => navigate(item.key === 'inbox' ? 'inbox' : item.key)}
                className={`relative overflow-hidden rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-300 ${
                  page === item.key
                    ? 'bg-indigo-600/15 text-indigo-300 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.2)]'
                    : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-100 hover:shadow-[inset_0_0_0_1px_rgba(148,163,184,0.1)]'
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
