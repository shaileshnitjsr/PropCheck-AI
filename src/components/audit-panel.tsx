'use client';

import { useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { Audit, IndiaContext, SourceSelection } from '@/lib/audit-contracts';
import { StoredDocument } from '@/lib/contracts';
import { LegalNotice } from './legal-notice';
import { RiskHeatmap } from './risk-heatmap';

const RULES = ['applicability', 'deposit', 'lock_in', 'notice', 'stamp', 'registration', 'escalation'];
const DEFAULT_INDIA: IndiaContext = { enabled: false, state: '', premises: 'unknown', model_act_applicable: false, monthly_rent: null, deposit: null, enabled_rules: RULES };

interface Props {
  result: Audit | null;
  available: boolean;
  busy: boolean;
  analyzing: boolean;
  onAnalyze: (india: IndiaContext) => Promise<void>;
  onSource: (selection: SourceSelection) => void;
  document?: StoredDocument | null;
  documents?: StoredDocument[];
  onSelectDocument?: (doc: StoredDocument) => void;
  error?: string;
}

export function AuditPanel({
  result,
  available,
  busy,
  analyzing,
  onAnalyze,
  onSource,
  document,
  documents,
  onSelectDocument,
  error,
}: Props) {
  const [india, setIndia] = useState<IndiaContext>(DEFAULT_INDIA);
  const [filter, setFilter] = useState('all');

  const hasDocument = available || !!document || Boolean(documents && documents.length > 0);
  const activeDoc = document ?? documents?.[0];

  return <section id="audit" className="studio-section dark-theme">
    <p className="text-xs uppercase tracking-widest text-studio-gray mb-4 font-mono font-semibold">04 / Evidence & review priorities</p>
    <h2 className="heading-display text-4xl md:text-6xl mb-6">Know What Needs a Closer Look</h2>
    <p className="text-sm max-w-2xl mb-6 text-studio-gray leading-relaxed">
      Review CUAD clause types with source locations, a published priority rubric, and draft negotiation language. An extracted quotation supports its location; it does not establish a legal conclusion.
    </p>

    {activeDoc && (
      <div className="flex flex-wrap items-center gap-3 mb-6 text-sm">
        <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 border border-white/15 rounded-lg text-xs shadow-sm">
          <FileText className="w-3.5 h-3.5 text-coral" />
          <span className="text-studio-gray">Target:</span>
          <span className="font-semibold text-white truncate max-w-[240px]">{activeDoc.filename}</span>
          {documents && documents.length > 1 && onSelectDocument && (
            <select
              aria-label="Select document for clause audit"
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

    <details className="border border-white/15 bg-white/[0.02] rounded-xl p-5 mb-6 shadow-sm">
      <summary className="cursor-pointer font-semibold text-white text-sm">India rent / lease checklist (optional)</summary>
      <label className="flex items-center gap-2 mt-4 text-sm text-gray-300">
        <input type="checkbox" checked={india.enabled} disabled={busy} onChange={e => setIndia({ ...india, enabled: e.target.checked })} className="rounded accent-coral" />
        Include the informational India checklist
      </label>
      {india.enabled && <div className="grid md:grid-cols-2 gap-4 mt-4 text-sm">
        <label className="text-gray-300 text-xs">State / Union Territory<input aria-label="State or Union Territory" value={india.state} maxLength={80} className="audit-input" onChange={e => setIndia({ ...india, state: e.target.value })} /></label>
        <label className="text-gray-300 text-xs">Premises<select aria-label="Premises type" className="audit-input cursor-pointer" value={india.premises} onChange={e => setIndia({ ...india, premises: e.target.value as IndiaContext['premises'] })}><option value="unknown">Not specified</option><option value="residential">Residential</option><option value="commercial">Commercial</option></select></label>
        <label className="text-gray-300 text-xs">Monthly rent (INR)<input className="audit-input" type="number" min="1" max="1000000000" value={india.monthly_rent ?? ''} onChange={e => setIndia({ ...india, monthly_rent: e.target.value ? Number(e.target.value) : null })} /></label>
        <label className="text-gray-300 text-xs">Deposit (INR)<input className="audit-input" type="number" min="0" max="10000000000" value={india.deposit ?? ''} onChange={e => setIndia({ ...india, deposit: e.target.value ? Number(e.target.value) : null })} /></label>
        <label className="md:col-span-2 flex items-start gap-2 text-xs text-gray-400 mt-1"><input type="checkbox" checked={india.model_act_applicable} onChange={e => setIndia({ ...india, model_act_applicable: e.target.checked })} className="mt-0.5 rounded accent-coral" />Compare my figures against the Model Tenancy Act benchmark as an assumption. This does not establish which state law applies.</label>
        <div className="md:col-span-2 flex flex-wrap gap-3 mt-2">{RULES.map(rule => <label key={rule} className="flex items-center gap-1.5 text-xs text-gray-300"><input type="checkbox" checked={india.enabled_rules.includes(rule)} onChange={e => setIndia({ ...india, enabled_rules: e.target.checked ? [...india.enabled_rules, rule] : india.enabled_rules.filter(item => item !== rule) })} className="rounded accent-coral" />{rule.replace('_', ' ')}</label>)}</div>
      </div>}
    </details>

    <div className="flex flex-col items-start gap-3">
      <button className="studio-btn" disabled={!hasDocument || busy} onClick={() => void onAnalyze(india)}>
        {analyzing && <Loader2 className="w-4 h-4 animate-spin" />}
        {analyzing ? 'Reviewing every chunk…' : 'Run clause audit'}
      </button>
      {!hasDocument && <p className="text-sm text-studio-gray">Upload a document to begin.</p>}
      {error && <p role="alert" className="text-xs text-coral border border-coral/30 bg-coral/10 p-3 rounded-lg max-w-xl">{error}</p>}
    </div>

    {result && <div className="mt-8 space-y-6">
      <div className="border border-coral/40 bg-coral/5 rounded-xl p-6 shadow-sm">
        <p className="uppercase text-xs tracking-widest text-studio-gray font-mono font-semibold">Overall review priority · {result.contract_type}</p>
        <p className="text-3xl font-bold my-3 text-coral tracking-tight">
          {result.overall_risk ? `${result.overall_risk.level.toUpperCase()} · ${result.overall_risk.score}/100` : 'Not scored — no verified passages'}
        </p>
        <p className="text-sm text-gray-200 leading-relaxed">{result.summary}</p>
        {result.overall_risk && <p className="text-xs text-gray-400 mt-3 leading-relaxed">{result.overall_risk.why}</p>}
        <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-white/10">Coverage: {result.analyzed_chunks}/{result.total_chunks} chunks processed · {result.dropped_claims} unsupported claims dropped. Coverage is not recall.</p>
        <details className="mt-4 text-xs text-gray-400"><summary className="cursor-pointer hover:text-white">How the score works</summary><p className="mt-2 text-gray-300">High 80: uncapped liability, non-compete, perpetual licence, covenant not to sue, or restrictive wording. Medium 50: material control/continuing-obligation types. Low 20: remaining extracted types. Overall = maximum clause score. Missing clauses never count as safe. Rule: review-priority-v1.</p></details>
      </div>
      <div className="flex gap-2 flex-wrap" aria-label="Filter review priority">{['all', 'high', 'medium', 'low'].map(value => <button key={value} aria-pressed={filter === value} className={`border px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === value ? 'border-coral bg-coral/15 text-coral' : 'border-white/20 text-gray-300 hover:border-white/40'}`} onClick={() => setFilter(value)}>{value.toUpperCase()}</button>)}</div>
      <RiskHeatmap audit={result} onSelect={clause => onSource({ docId: result.doc_id, location: clause.location, quote: clause.quoted_text })} />
      {result.clauses.filter(clause => filter === 'all' || clause.risk.level === filter).map(clause => <article key={clause.id} className="border border-white/15 bg-white/[0.02] rounded-xl p-5 space-y-3 shadow-sm">
        <div className="flex flex-wrap justify-between items-center gap-2">
          <h3 className="font-bold text-base text-white">{clause.type}</h3>
          <span className="text-xs uppercase font-mono px-2.5 py-0.5 rounded-full bg-coral/15 text-coral border border-coral/30 font-semibold">{clause.risk.level} · Score {clause.risk.score}</span>
        </div>
        <p className="text-xs text-gray-400">Party: {clause.party} · Model confidence: {clause.confidence.toFixed(2)} (uncalibrated)</p>
        <blockquote className="border-l-2 border-coral pl-3 text-sm text-gray-200 whitespace-pre-wrap leading-relaxed bg-white/[0.02] p-2 rounded">{clause.quoted_text}</blockquote>
        <button className="text-xs underline text-coral hover:text-red-400 font-medium block" onClick={() => onSource({ docId: result.doc_id, location: clause.location, quote: clause.quoted_text })}>View source · {clause.location.page ? `page ${clause.location.page} · ` : ''}{clause.location.section_id}</button>
        <p className="text-sm text-gray-300 leading-relaxed">{clause.risk.why}</p>
        {clause.redline && <details className="bg-white/5 border border-white/10 rounded-lg p-3.5 text-sm"><summary className="cursor-pointer font-semibold text-white">Negotiation draft — review before use</summary><p className="text-xs uppercase tracking-wider text-gray-400 mt-3 font-mono">Original</p><p className="mt-1 whitespace-pre-wrap text-gray-300">{clause.redline.original}</p><p className="text-xs uppercase tracking-wider text-coral mt-3 font-mono">Suggested replacement</p><p className="mt-1 whitespace-pre-wrap text-emerald-300">{clause.redline.suggested}</p><p className="text-xs text-gray-400 mt-3">{clause.redline.rationale}</p><LegalNotice /></details>}
      </article>)}
      {result.clauses.length === 0 && <p className="text-sm text-gray-400 italic">No source-located CUAD clauses were returned. This does not establish absence or low risk.</p>}
      {result.rule_checks.length > 0 && <div className="space-y-4"><h3 className="text-2xl font-bold text-white">India checklist</h3>{result.rule_checks.map(check => <article key={check.id} className="border border-white/15 bg-white/[0.02] rounded-xl p-5 text-sm shadow-sm"><div className="flex flex-wrap items-center justify-between gap-2 mb-2"><h4 className="font-bold text-base text-white">{check.title}</h4><span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-white/10 text-gray-300 font-semibold">{check.status.replaceAll('_', ' ')}</span></div><p className="my-3 text-gray-300 leading-relaxed">{check.detail}</p><a className="underline text-coral hover:text-red-400 font-medium" href={check.source_url} target="_blank" rel="noreferrer">{check.source_title} · {check.section}</a>{check.evidence.map((location, index) => <button key={index} className="block underline text-xs text-gray-400 hover:text-white mt-2" onClick={() => onSource({ docId: result.doc_id, location, quote: '' })}>Inspect checklist evidence {index + 1}</button>)}<LegalNotice /></article>)}</div>}
      <details className="text-xs text-gray-400"><summary className="cursor-pointer hover:text-white">Coverage and limitations</summary><ul className="list-disc pl-5 mt-3 space-y-2">{result.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul><p className="mt-3">Workflow: {result.steps.join(' → ')}</p></details>
    </div>}
    <LegalNotice />
  </section>;
}
