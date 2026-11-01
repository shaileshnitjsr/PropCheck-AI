'use client';

import { useEffect, useRef, useState } from 'react';
import { BarChart3, FileText, Loader2 } from 'lucide-react';
import { BenefitsResult, Finding, StoredDocument } from '@/lib/contracts';
import { LegalNotice } from './legal-notice';

interface Props {
  result: BenefitsResult | null;
  available: boolean;
  busy: boolean;
  analyzing: boolean;
  onAnalyze: () => Promise<void>;
  document?: StoredDocument | null;
  documents?: StoredDocument[];
  onSelectDocument?: (doc: StoredDocument) => void;
  error?: string;
}

export function BenefitsPanel({
  result,
  available,
  busy,
  analyzing,
  onAnalyze,
  document,
  documents,
  onSelectDocument,
  error,
}: Props) {
  const [selected, setSelected] = useState<Finding | null>(null);
  const quote = useRef<HTMLDivElement>(null);
  useEffect(() => { setSelected(null); }, [result]);
  useEffect(() => { if (selected) quote.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, [selected]);
  const parties = Array.from(new Set(result?.items.map(item => item.party) || []));
  const hasDocument = available || !!document || Boolean(documents && documents.length > 0);
  const activeDoc = document ?? documents?.[0];

  return <section id="benefits" className="studio-section dark-theme">
    <p className="text-xs uppercase tracking-widest text-studio-gray mb-4 font-mono font-semibold">02 / Benefits & obligations</p>
    <h2 className="heading-display text-4xl md:text-6xl mb-6">Read the Balance</h2>
    <p className="text-sm text-studio-gray max-w-xl mb-6 leading-relaxed">
      Analyze every indexed chunk. Scores describe estimated significance, not fairness, enforceability, or legal risk.
    </p>

    {activeDoc && (
      <div className="flex flex-wrap items-center gap-3 mb-6 text-sm">
        <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 border border-white/15 rounded-lg text-xs shadow-sm">
          <FileText className="w-3.5 h-3.5 text-coral" />
          <span className="text-studio-gray">Target:</span>
          <span className="font-semibold text-white truncate max-w-[240px]">{activeDoc.filename}</span>
          {documents && documents.length > 1 && onSelectDocument && (
            <select
              aria-label="Select document for benefits analysis"
              value={activeDoc.doc_id}
              onChange={e => {
                const found = documents.find(d => d.doc_id === e.target.value);
                if (found) onSelectDocument(found);
              }}
              className="bg-white/10 hover:bg-white/15 border border-white/20 text-xs text-white px-2 py-0.5 ml-2 rounded cursor-pointer focus:outline-none focus:ring-1 focus:ring-coral transition-colors"
            >
              {documents.map(d => (
                <option key={d.doc_id} value={d.doc_id} className="bg-[#151515] text-white">
                  {d.filename}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
    )}

    <div className="flex flex-col items-start gap-3 mb-6">
      <button disabled={!hasDocument || busy} onClick={() => void onAnalyze()} className="studio-btn">
        {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
        {analyzing ? 'Analyzing all chunks…' : result ? 'Analyze again' : 'Analyze document'}
      </button>
      {!hasDocument && <p className="text-sm text-studio-gray">Upload a document to begin.</p>}
      {error && <p role="alert" className="text-xs text-coral border border-coral/30 bg-coral/10 p-3 max-w-xl">{error}</p>}
    </div>

    {result && <>
      <p role="status" className="text-xs mb-6">{result.analyzed_chunks} / {result.total_chunks} chunks processed · {result.items.length} findings. Coverage counts processed chunks; it does not guarantee every clause was identified.</p>
      {result.items.length === 0 && <p>No supported benefits or obligations were identified.</p>}
      <div className="grid md:grid-cols-2 gap-6 w-full">
        {parties.map(party => <div key={party} className="studio-card p-6">
          <h3 className="font-bold text-lg mb-4">{party}</h3>
          <div className="space-y-4">{result.items.filter(item => item.party === party).map((item, index) =>
            <button key={`${item.chunk_ids.join('-')}-${index}`} className="w-full text-left group" onClick={() => setSelected(item)}>
              <span className="flex justify-between gap-4 text-sm"><span>{item.benefit}</span><span>{item.score}/10</span></span>
              <span className="block text-[10px] uppercase text-studio-gray mt-1">{item.kind} · view source quotation</span>
              <span className="block bg-white/10 h-2 mt-2"><span className="block bg-coral h-2 group-hover:bg-white" style={{ width: `${item.score * 10}%` }} /></span>
            </button>)}</div>
        </div>)}
      </div>
      {selected && <div ref={quote} className="studio-card w-full p-6 mt-6 border-l-4 border-coral" aria-label="Source quotation">
        <p className="font-semibold mb-3">{selected.party} — {selected.benefit}</p>
        <blockquote className="whitespace-pre-wrap text-sm leading-relaxed">“{selected.clause}”</blockquote>
        <p className="text-xs text-studio-gray mt-3">Source chunks: {selected.chunk_ids.join(', ')}</p>
      </div>}
    </>}
    <LegalNotice />
  </section>;
}
