import { useState, useMemo } from 'react'
import { useThread } from '../hooks/useApi.js'

/* ------------------------------------------------------------------ */
/* Helper Components                                                   */
/* ------------------------------------------------------------------ */

function Badge({ label, className }) {
  if (!label) return null
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${className}`}>
      {label}
    </span>
  )
}

function ContactCard({ contact, email }) {
  if (!contact) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 mb-6">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Customer Profile</h3>
        <p className="text-slate-300">No profile found for <span className="text-indigo-400">{email}</span></p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 mb-6 flex items-start justify-between">
      <div>
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Customer Profile</h3>
        <div className="flex items-center gap-3 mb-1">
          <span className="text-lg font-bold text-white">{contact.name || 'Unknown Name'}</span>
          <Badge label={contact.status} className="bg-blue-500/20 text-blue-300" />
        </div>
        <p className="text-slate-400">{contact.company || 'Unknown Company'} &bull; {contact.email}</p>
      </div>
      <div className="text-right">
        <p className="text-sm text-slate-400 mb-1">Account Value</p>
        <p className="text-xl font-bold text-green-400">${contact.account_value.toLocaleString()}</p>
        {contact.churn_risk_score && (
          <p className="text-xs text-slate-500 mt-1">Churn Risk: {contact.churn_risk_score.toFixed(2)}</p>
        )}
      </div>
    </div>
  )
}

function EmailItem({ email, isSelected, onClick }) {
  const date = new Date(email.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  
  return (
    <div 
      onClick={onClick}
      className={`p-4 cursor-pointer border-b border-slate-800/50 transition-colors ${
        isSelected ? 'bg-indigo-900/20 border-l-2 border-l-indigo-500' : 'hover:bg-slate-800/40 border-l-2 border-l-transparent'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="font-medium text-slate-200 truncate pr-4">{email.subject}</span>
        <span className="text-xs text-slate-500 whitespace-nowrap">{date}</span>
      </div>
      <p className="text-sm text-slate-400 line-clamp-2 mb-3">{email.body}</p>
      <div className="flex gap-2 flex-wrap">
        <Badge label={email.category} className="bg-slate-700/50 text-slate-300" />
        <Badge label={email.urgency} className="bg-slate-700/50 text-slate-300" />
        <Badge label={email.status} className="bg-indigo-500/20 text-indigo-300" />
      </div>
    </div>
  )
}

function AgentLogViewer({ action }) {
  if (!action || !action.agent_reasoning_log) return null
  const log = Array.isArray(action.agent_reasoning_log) ? action.agent_reasoning_log : [action.agent_reasoning_log]

  return (
    <div className="mt-6 rounded-lg border border-slate-800 bg-slate-950 p-4">
      <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
        Agent Reasoning Trace
      </h4>
      <div className="space-y-4">
        {log.map((step, idx) => (
          <div key={idx} className="border-l-2 border-slate-800 pl-4 py-1">
            {step.step && <p className="text-xs text-slate-500 mb-1">Step {step.step}</p>}
            {step.thought && <p className="text-sm text-slate-300 italic mb-2">"{step.thought}"</p>}
            {step.action && (
              <div className="bg-slate-900 rounded p-2 mb-2">
                <p className="text-xs font-mono text-indigo-400 break-all">
                  &gt; {step.action}({JSON.stringify(step.input || {})})
                </p>
              </div>
            )}
            {step.observation && (
              <p className="text-xs text-slate-400 bg-slate-900/50 rounded p-2 border border-slate-800/50">
                {typeof step.observation === 'object' ? JSON.stringify(step.observation) : step.observation}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function DraftViewer({ draft, onRefetch }) {
  const [isEditing, setIsEditing] = useState(false)
  const [content, setContent] = useState(draft ? draft.content : '')
  const [loading, setLoading] = useState(false)

  if (!draft) return null

  const handleApprove = async () => {
    setLoading(true)
    try {
      const { approveDraft } = await import('../hooks/useApi.js')
      await approveDraft(draft.id)
      if (onRefetch) onRefetch()
    } catch (e) {
      alert("Failed to approve draft: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveEdit = async () => {
    setLoading(true)
    try {
      const { editDraft } = await import('../hooks/useApi.js')
      await editDraft(draft.id, content)
      setIsEditing(false)
      if (onRefetch) onRefetch()
    } catch (e) {
      alert("Failed to save draft: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-6 rounded-lg border border-indigo-900/50 bg-indigo-950/20 p-4">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-2">
          Proposed Draft Reply
        </h4>
        <Badge label={draft.status} className="bg-yellow-500/20 text-yellow-300" />
      </div>
      
      {isEditing ? (
        <textarea
          className="w-full bg-slate-900 rounded border border-slate-700 p-4 text-sm text-slate-300 focus:outline-none focus:border-indigo-500 min-h-[150px]"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      ) : (
        <div className="bg-slate-900 rounded border border-slate-800 p-4 whitespace-pre-wrap text-sm text-slate-300">
          {draft.content}
        </div>
      )}

      {draft.status === 'Pending' && (
        <div className="mt-4 flex gap-3">
          {isEditing ? (
            <>
              <button 
                onClick={handleSaveEdit}
                disabled={loading}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors disabled:opacity-50"
              >
                Save
              </button>
              <button 
                onClick={() => { setIsEditing(false); setContent(draft.content) }}
                className="rounded border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={handleApprove}
                disabled={loading}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors disabled:opacity-50"
              >
                Approve & Send
              </button>
              <button 
                onClick={() => setIsEditing(true)}
                className="rounded border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Edit Draft
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function ThreadWorkspace({ contactEmail, onBack }) {
  const { data, loading, error, refetch } = useThread(contactEmail)
  const [selectedEmailId, setSelectedEmailId] = useState(null)

  const emails = data?.emails || []
  const actions = data?.actions || []
  const drafts = data?.drafts || []

  // Auto-select first email when loaded
  useMemo(() => {
    if (emails.length > 0 && !selectedEmailId) {
      setSelectedEmailId(emails[0].id)
    }
  }, [emails, selectedEmailId])

  const selectedEmail = emails.find(e => e.id === selectedEmailId)
  
  // Find related agent logs and drafts for selected email
  const emailActions = actions.filter(a => a.email_id === selectedEmailId)
  const agentLogAction = emailActions.find(a => a.action_type === 'Agent-Triage')
  const emailDrafts = drafts.filter(d => d.email_id === selectedEmailId)

  if (loading) {
    return <div className="text-center py-20 text-slate-500">Loading thread data...</div>
  }

  if (error) {
    return (
      <div>
        <button onClick={onBack} className="mb-4 text-sm text-indigo-400 hover:text-indigo-300">&larr; Back to Inbox</button>
        <div className="p-4 bg-red-900/20 border border-red-900 text-red-400 rounded-md">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={onBack}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors"
        >
          &larr; Back
        </button>
        <h2 className="text-xl font-bold text-white">Thread Workspace</h2>
      </div>

      <ContactCard contact={data?.contact} email={contactEmail} />

      <div className="flex flex-1 gap-6 min-h-0">
        {/* Left pane: Email list */}
        <div className="w-1/3 flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900">
            <h3 className="font-semibold text-slate-300">Conversation History</h3>
            <p className="text-xs text-slate-500">{emails.length} message{emails.length !== 1 ? 's' : ''}</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {emails.map(email => (
              <EmailItem 
                key={email.id} 
                email={email} 
                isSelected={selectedEmailId === email.id}
                onClick={() => setSelectedEmailId(email.id)}
              />
            ))}
          </div>
        </div>

        {/* Right pane: Email details & Agent UI */}
        <div className="w-2/3 flex flex-col rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden">
          {selectedEmail ? (
            <div className="flex-1 overflow-y-auto p-6">
              {/* Email Content */}
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white mb-4">{selectedEmail.subject}</h2>
                <div className="flex items-center justify-between text-sm text-slate-400 mb-6 pb-4 border-b border-slate-800">
                  <div>
                    <span className="font-medium text-slate-300">From:</span> {selectedEmail.sender}
                  </div>
                  <div>{new Date(selectedEmail.timestamp).toLocaleString()}</div>
                </div>
                <div className="whitespace-pre-wrap text-slate-300 font-sans leading-relaxed">
                  {selectedEmail.body}
                </div>
              </div>

              {/* AI Metadata badges */}
              <div className="flex flex-wrap gap-4 mb-8 p-4 bg-slate-950 rounded-lg border border-slate-800">
                <div>
                  <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Category</p>
                  <p className="text-sm font-medium text-slate-200">{selectedEmail.category}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Urgency</p>
                  <p className="text-sm font-medium text-slate-200">{selectedEmail.urgency}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Sentiment</p>
                  <p className="text-sm font-medium text-slate-200">
                    {selectedEmail.sentiment_score !== null ? selectedEmail.sentiment_score.toFixed(2) : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Human Req.</p>
                  <p className={`text-sm font-medium ${selectedEmail.requires_human ? 'text-orange-400' : 'text-slate-200'}`}>
                    {selectedEmail.requires_human ? 'Yes' : 'No'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Confidence</p>
                  <p className="text-sm font-medium text-slate-200">
                    {selectedEmail.confidence !== null ? (selectedEmail.confidence * 100).toFixed(0) + '%' : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Non-triage Actions (e.g. Escalate, Ticket, Legal) */}
              {emailActions.filter(a => a.action_type !== 'Agent-Triage').map(action => (
                <div key={action.id} className="mb-6 p-4 rounded-lg border border-orange-900/50 bg-orange-950/20">
                  <h4 className="text-sm font-semibold text-orange-400 uppercase tracking-wider mb-2">
                    Action Taken: {action.action_type}
                  </h4>
                  <p className="text-sm text-slate-300">{action.proposed_content}</p>
                </div>
              ))}

              {/* Drafts */}
              {emailDrafts.map(draft => (
                <DraftViewer key={draft.id} draft={draft} onRefetch={refetch} />
              ))}

              {/* Agent Reasoning */}
              <AgentLogViewer action={agentLogAction} />

            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-slate-500">
              Select a message to view details
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
