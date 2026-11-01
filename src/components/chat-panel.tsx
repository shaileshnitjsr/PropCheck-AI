'use client';

import { useEffect, useRef, useState } from 'react';
import { FileText, Loader2, Send } from 'lucide-react';
import { Message, StoredDocument } from '@/lib/contracts';
import { SourceSelection } from '@/lib/audit-contracts';
import { LegalNotice } from './legal-notice';

const QUESTIONS = [
  ['Who benefits most?', 'Which party benefits most from the available excerpts and why?'],
  ['Breach consequences', 'What happens if either party breaches this agreement?'],
  ['Liability & risks', 'What are the liability clauses and who bears the most risk?'],
  ['Termination', 'Under what conditions can this agreement be terminated, and by whom?'],
  ['Unfair clauses', 'Are there any potentially one-sided clauses in the retrieved excerpts?'],
  ['Plain summary', 'Summarize the available contract excerpts in plain English.'],
  ['Key obligations', 'What are the key obligations for each party?'],
  ['Dispute resolution', 'How are disputes handled between the parties?'],
];

interface Props {
  messages: Message[];
  available: boolean;
  busy: boolean;
  sending: boolean;
  onSend: (question: string) => Promise<boolean>;
  draft?: string;
  docId?: string;
  onSource?: (selection: SourceSelection) => void;
  document?: StoredDocument | null;
  documents?: StoredDocument[];
  onSelectDocument?: (doc: StoredDocument) => void;
  error?: string;
}

export function ChatPanel({
  messages,
  available,
  busy,
  sending,
  onSend,
  draft,
  docId,
  onSource,
  document,
  documents,
  onSelectDocument,
  error,
}: Props) {
  const [input, setInput] = useState('');
  const [expanded, setExpanded] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (messages.length) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages]);

  const hasDocument = available || !!document || !!docId || Boolean(documents && documents.length > 0);
  const activeDoc = document ?? (docId ? documents?.find(d => d.doc_id === docId) : documents?.[0]);

  async function submit(question: string) {
    if (!question.trim() || busy || !hasDocument) return;
    if (await onSend(question)) setInput('');
  }

  return <section id="chat" className="studio-section cream-theme">
    <p className="text-xs uppercase tracking-widest text-[#1d1c19]/60 mb-4 font-mono font-semibold">03 / Ask your contract</p>
    <h2 className="heading-display text-4xl md:text-6xl mb-6">Clarity in Context</h2>
    <div className={`${expanded ? 'fixed inset-4 z-[60] bg-[#f4ead4] p-6 overflow-auto shadow-2xl rounded-2xl' : 'w-full'}`}>
      <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
        <div className="flex items-center gap-3">
          <h3 className="font-bold text-base text-[#1d1c19]">AI auditor</h3>
          {activeDoc && (
            <div className="flex items-center gap-1.5 text-xs bg-white/70 border border-[#1d1c19]/20 px-2.5 py-1 rounded-md shadow-sm">
              <FileText className="w-3.5 h-3.5 text-coral" />
              <span className="font-semibold truncate max-w-[200px] text-[#1d1c19]">{activeDoc.filename}</span>
              {documents && documents.length > 1 && onSelectDocument && (
                <select
                  aria-label="Select contract for chat"
                  value={activeDoc.doc_id}
                  onChange={e => {
                    const found = documents.find(d => d.doc_id === e.target.value);
                    if (found) onSelectDocument(found);
                  }}
                  className="bg-white/80 hover:bg-white border border-[#1d1c19]/25 text-xs text-[#1d1c19] px-1.5 py-0.5 ml-1.5 rounded cursor-pointer focus:outline-none focus:ring-1 focus:ring-coral"
                >
                  {documents.map(d => (
                    <option key={d.doc_id} value={d.doc_id} className="text-black bg-[#f4ead4]">
                      {d.filename}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>
        <button className="text-xs underline text-[#1d1c19]/70 hover:text-[#1d1c19] ml-auto font-medium" onClick={() => setExpanded(value => !value)}>
          {expanded ? 'Exit full screen' : 'Full screen'}
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {QUESTIONS.map(([label, question]) =>
          <button
            key={label}
            disabled={!hasDocument || busy}
            className="text-xs border border-[#1d1c19]/25 bg-white/50 hover:bg-white px-3 py-1.5 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-[#1d1c19]"
            onClick={() => void submit(question)}
          >
            {label}
          </button>
        )}
      </div>
      <div className="border border-[#1d1c19]/20 bg-white/60 rounded-xl p-5 min-h-[220px] max-h-[55vh] overflow-y-auto shadow-sm" aria-live="polite" role="log" aria-label="Contract chat">
        {messages.length === 0 && (
          <p className="text-sm text-[#1d1c19]/60">
            {hasDocument
              ? 'Ask a question. Answers use four retrieved excerpts and stream as an unverified draft until validation finishes.'
              : 'Upload a contract to start chatting.'}
          </p>
        )}
        {messages.map((message, index) => <article key={index} className={`mb-6 ${message.role === 'user' ? 'pl-8' : ''}`}>
          <p className="text-xs uppercase tracking-wider font-bold mb-2 text-[#1d1c19]">{message.role === 'user' ? 'You' : 'ContractIQ'}</p>
          <p className="text-sm leading-relaxed whitespace-pre-wrap text-[#1d1c19]">{message.content}</p>
          {message.sources?.map(source => <details key={source.excerpt} className="mt-3 text-xs border-l-2 border-coral pl-3 py-1">
            <summary className="cursor-pointer font-medium text-[#1d1c19]">Excerpt {source.excerpt}{source.page ? ` · Page ${source.page}` : ''} · {source.chunk_id}</summary>
            <blockquote className="mt-2 whitespace-pre-wrap leading-relaxed text-[#1d1c19]/80 bg-white/60 p-2 rounded">{source.preview}</blockquote>
            {(docId || activeDoc?.doc_id) && onSource && (
              <button
                className="underline mt-2 text-coral hover:text-red-700 font-medium block"
                onClick={() => onSource({ docId: docId || activeDoc!.doc_id, location: source, quote: source.preview })}
              >
                Highlight on source
              </button>
            )}
          </details>)}
          {message.role === 'assistant' && <LegalNotice />}
        </article>)}
        {sending && <p className="flex items-center gap-2 text-sm text-[#1d1c19]"><Loader2 className="w-4 h-4 animate-spin text-coral" /> {draft ? 'Unverified draft — checking citations before saving' : 'Retrieving and checking excerpts…'}</p>}
        {sending && draft && <div className="border border-dashed border-[#1d1c19]/30 bg-white/70 rounded-lg p-3.5 mt-3"><p className="text-sm whitespace-pre-wrap text-[#1d1c19]">{draft}</p><LegalNotice /></div>}
        {error && <p role="alert" className="text-xs text-coral border border-coral/30 bg-coral/10 p-3 rounded-lg mt-3">{error}</p>}
        <div ref={end} />
      </div>
      <form className="flex gap-2.5 mt-4" onSubmit={event => { event.preventDefault(); void submit(input); }}>
        <input
          aria-label="Question about contract"
          value={input}
          onChange={event => setInput(event.target.value)}
          maxLength={2000}
          disabled={!hasDocument || busy}
          placeholder={hasDocument ? "Ask about a clause, obligation, or consequence…" : "Upload a contract to start chatting…"}
          className="flex-1 min-w-0 border border-[#1d1c19]/25 bg-white/80 hover:bg-white focus:bg-white focus:border-coral focus:ring-2 focus:ring-coral/20 rounded-xl p-3.5 text-sm outline-none transition-all placeholder:text-[#1d1c19]/45 text-[#1d1c19] shadow-sm disabled:opacity-50"
        />
        <button
          aria-label="Send question"
          disabled={!hasDocument || busy || !input.trim()}
          className="studio-btn px-5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
      <LegalNotice />
    </div>
  </section>;
}
