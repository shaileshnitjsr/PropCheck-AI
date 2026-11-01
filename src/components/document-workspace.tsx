'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { StoredDocument } from '@/lib/contracts';
import { SourceSelection } from '@/lib/audit-contracts';
import { WorkspaceAnswer } from '@/lib/product-contracts';
import { LegalNotice } from './legal-notice';

export function DocumentWorkspace({ revision, onOpen, onSource, onRemove }: { revision: string; onOpen: (doc: StoredDocument) => Promise<void>; onSource: (value: SourceSelection) => void; onRemove?: (id: string) => Promise<void> }) {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<WorkspaceAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    const version = ++generation.current;
    setAnswer(null); setBusy(false);
    api.documents().then(result => {
      if (version !== generation.current) return;
      setDocuments(result); setSelected(ids => ids.filter(id => result.some(doc => doc.doc_id === id))); setError('');
    }).catch(failure => { if (version === generation.current) { setDocuments([]); setSelected([]); setError(failure.message); } });
    return () => { generation.current = version + 1; };
  }, [revision, refresh]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || selected.length < 1 || !question.trim()) return;
    const version = generation.current;
    setBusy(true); setAnswer(null); setError('');
    try { const result = await api.workspaceChat(selected, question.trim()); if (generation.current === version) setAnswer(result); }
    catch (failure) { if (generation.current === version) setError(failure instanceof Error ? failure.message : 'The question failed.'); }
    finally { if (generation.current === version) setBusy(false); }
  }
  return <section id="workspace" className="studio-section bg-[#ece9e0] text-[#151515]">
    <p className="text-xs uppercase tracking-widest text-[#151515]/60 mb-4 font-mono font-semibold">Workspace / Across your documents</p>
    <h2 className="heading-display text-4xl md:text-6xl mb-6">See the Differences Together</h2>
    <p className="text-sm text-[#151515]/80 max-w-2xl mb-6 leading-relaxed">
      Select one or more ready documents. Each answer samples up to two excerpts per document and identifies its sources. Missing evidence does not mean a clause is absent.
    </p>
    <div className="flex items-center gap-4 mb-5">
      <button className="underline text-sm font-semibold hover:text-black transition-colors" disabled={busy} onClick={() => setRefresh(n => n + 1)}>
        Refresh documents
      </button>
      {onRemove && documents.length > 0 && (
        <button
          className="text-xs text-coral hover:text-red-700 hover:underline font-semibold transition-colors"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              for (const doc of documents) {
                await onRemove(doc.doc_id);
              }
              setRefresh(n => n + 1);
            } catch (err) {
              setError(err instanceof Error ? err.message : 'Failed to clear documents');
            } finally {
              setBusy(false);
            }
          }}
        >
          Clear all documents
        </button>
      )}
    </div>
    {!documents.length && (
      <div className="p-8 text-center border-2 border-dashed border-black/15 bg-white/40 rounded-xl mb-6">
        <p className="text-sm text-[#151515]/70 font-medium">Upload documents to build your workspace. Only ready, unexpired documents appear here.</p>
      </div>
    )}
    <div className="grid md:grid-cols-2 gap-3.5 mb-6">
      {documents.map((doc, index) => {
        const isChecked = selected.includes(doc.doc_id);
        return (
          <div
            key={doc.doc_id}
            className={`p-4 rounded-xl border transition-all ${
              isChecked
                ? 'bg-white border-coral shadow-sm ring-1 ring-coral/30'
                : 'bg-white/70 border-black/15 hover:border-black/30 hover:bg-white'
            }`}
          >
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isChecked}
                disabled={busy || (!isChecked && selected.length >= 5)}
                onChange={e => {
                  setSelected(ids => e.target.checked ? [...ids, doc.doc_id] : ids.filter(id => id !== doc.doc_id));
                  setAnswer(null);
                }}
                className="mt-1 rounded accent-coral"
              />
              <span className="break-all flex-1 min-w-0">
                <span className="font-semibold text-sm block text-[#151515]">{doc.filename}</span>
                <span className="block text-xs text-[#151515]/60 mt-1">
                  {doc.num_chunks} chunks · Expires {new Date(doc.expires_at * 1000).toLocaleString()}
                </span>
              </span>
            </label>
            <div className="flex items-center gap-4 mt-3 pt-2.5 border-t border-black/10">
              <button
                className="underline text-xs text-[#151515]/80 hover:text-[#151515] font-medium"
                disabled={busy}
                onClick={() => void onOpen(doc)}
              >
                Open document {index + 1}
              </button>
              {onRemove && (
                <button
                  className="text-xs text-coral hover:text-red-700 hover:underline font-medium"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await onRemove(doc.doc_id);
                      setRefresh(n => n + 1);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to remove document');
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
    <form onSubmit={submit} className="space-y-4">
      <label className="block text-sm font-semibold text-[#151515]">
        Question across selected documents
        <textarea
          className="block w-full border border-black/20 bg-white/90 hover:bg-white focus:bg-white focus:border-coral focus:ring-2 focus:ring-coral/20 rounded-xl p-3.5 mt-2 text-sm outline-none transition-all placeholder:text-black/40 text-[#151515] shadow-sm"
          placeholder="Ask a question comparing clauses, penalties, or timelines across your selected documents…"
          maxLength={2000}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          disabled={busy}
        />
      </label>
      <div className="flex items-center gap-3">
        <button className="studio-btn" disabled={busy || selected.length < 1 || !question.trim()}>
          {busy ? 'Checking selected documents…' : 'Ask across documents'}
        </button>
        <span className="text-xs text-[#151515]/70 font-medium">
          {selected.length}/5 selected
        </span>
      </div>
    </form>
    {error && <p role="alert" className="mt-4 text-xs text-coral bg-coral/10 border border-coral/30 p-3 rounded-lg">{error}</p>}
    {answer && (
      <div aria-label="Workspace answer" className="mt-6 border-t border-black/15 pt-6 space-y-4">
        <div className="bg-white/80 p-5 rounded-xl border border-black/10 shadow-sm">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#151515] font-medium">{answer.answer}</p>
        </div>
        {answer.sources.map(source => (
          <details key={source.excerpt} className="border border-black/15 bg-white/60 p-4 rounded-xl shadow-sm text-xs">
            <summary className="cursor-pointer font-semibold text-[#151515]">Excerpt {source.excerpt} · {source.filename}</summary>
            <blockquote className="text-sm my-3 whitespace-pre-wrap leading-relaxed text-[#151515]/80 bg-white/80 p-3 rounded-lg border-l-2 border-coral">{source.preview}</blockquote>
            <button className="underline text-xs text-coral hover:text-red-700 font-semibold mt-1" onClick={() => onSource({ docId: source.doc_id, location: source, quote: source.preview })}>
              View workspace source {source.excerpt}
            </button>
          </details>
        ))}
        <p className="text-xs text-[#151515]/60">{answer.disclaimer}</p>
      </div>
    )}
    <LegalNotice />
  </section>;
}
