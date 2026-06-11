// Phase 12: Thread Workspace — placeholder until implementation
export default function ThreadWorkspace({ contactEmail, onBack }) {
  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
      >
        &larr; Back to Inbox
      </button>
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-8 text-center">
        <h2 className="text-lg font-semibold text-white mb-2">Thread Workspace</h2>
        <p className="text-slate-400">
          Viewing threads for <span className="text-indigo-400 font-medium">{contactEmail}</span>
        </p>
        <p className="text-slate-500 text-sm mt-2">Full implementation coming in Phase 12.</p>
      </div>
    </div>
  )
}
