'use client';

import { useState, useRef } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Download, ExternalLink, Loader2, MapPin, Shield, RefreshCw, Upload, Trash2, CheckSquare, Square } from 'lucide-react';
import { api } from '@/lib/api';
import { StoredDocument } from '@/lib/contracts';
import { SourceSelection } from '@/lib/audit-contracts';
import { PropertyDueDiligenceReport } from '@/lib/property-contracts';

const SUPPORTED_STATES = [
  'Maharashtra',
  'Karnataka',
  'Delhi',
  'Uttar Pradesh',
  'Haryana',
  'Telangana',
  'Tamil Nadu',
  'Gujarat',
  'Rajasthan',
  'West Bengal',
  'Kerala',
  'Punjab',
  'Goa',
];

interface Props {
  documents: StoredDocument[];
  busy: boolean;
  onSource: (source: SourceSelection) => void;
  onOpenDoc: (doc: StoredDocument) => Promise<void>;
  onRemoveDoc?: (id: string) => Promise<void>;
  onUpload?: (fileOrFiles: File | File[]) => Promise<boolean>;
}

export function PropCheckDashboard({ documents, busy, onSource, onOpenDoc, onRemoveDoc, onUpload }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [stateOverride, setStateOverride] = useState<string>('');
  const [report, setReport] = useState<PropertyDueDiligenceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string>('');
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  async function runDueDiligence() {
    if (selectedIds.length === 0) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.propertyDueDiligence(selectedIds, stateOverride || undefined);
      setReport(res);
      if (!stateOverride && res.detected_state && res.detected_state !== 'UNKNOWN') {
        setStateOverride(res.detected_state);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Due diligence analysis failed.');
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    if (!report || selectedIds.length === 0) return;
    setDownloading(true);
    try {
      const blob = await api.propertyPdfReport(selectedIds, stateOverride || undefined);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PropCheck-${report.property_name.replace(/\s+/g, '_')}-Audit.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate PDF report.');
    } finally {
      setDownloading(false);
    }
  }

  const filteredFindings = (report?.cross_document_findings || []).filter(f => {
    if (filterSeverity === 'ALL') return true;
    if (filterSeverity === 'CRITICAL_HIGH') return f.severity === 'CRITICAL' || f.severity === 'HIGH';
    if (filterSeverity === 'PASS') return f.severity === 'PASS';
    return f.severity === filterSeverity;
  });

  return (
    <section id="propcheck" className="studio-section bg-[#121212] text-white py-12 px-6 md:px-12 border-t border-white/10">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-[#ff4e3a] mb-2 font-mono">
              <Shield className="w-4 h-4" />
              <span>PropCheck AI · Due-Diligence Engine</span>
            </div>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-white">
              Property Due-Diligence & Consistency
            </h2>
            <p className="text-sm text-gray-400 mt-2 max-w-2xl">
              Compare property identifiers, carpet area, payment consideration, and official RERA records across your documents.
            </p>
          </div>

          {report && (
            <button
              onClick={downloadReport}
              disabled={downloading}
              className="flex items-center justify-center gap-2 bg-[#ff4e3a] hover:bg-[#e03d2a] text-white px-5 py-3 text-sm font-semibold tracking-wide transition-all rounded shadow-lg disabled:opacity-50"
            >
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span>Download PDF Audit Report</span>
            </button>
          )}
        </div>

        {/* Document Selection & State Control */}
        <div className="bg-[#1c1c1c] border border-white/10 rounded-lg p-6 mb-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4 pb-4 border-b border-white/10">
            <div>
              <h3 className="text-base font-semibold text-white">Select Documents for Cross-Verification</h3>
              <p className="text-xs text-gray-400 mt-1">
                Select 1 or more documents (e.g., Sale Deed, Allotment Letter, Builder Agreement).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Direct Upload in PropCheck */}
              {onUpload && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,application/pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.txt,text/plain,.md,text/markdown"
                    className="sr-only"
                    onChange={e => {
                      const files = e.target.files ? Array.from(e.target.files) : [];
                      if (files.length > 0) void onUpload(files);
                      e.target.value = '';
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={busy}
                    className="flex items-center gap-1.5 bg-[#ff4e3a] hover:bg-[#e03d2a] text-white px-3 py-1.5 text-xs font-semibold rounded transition-colors disabled:opacity-50"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Property Documents</span>
                  </button>
                </>
              )}

              {/* State selection */}
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-[#ff4e3a]" />
                <label htmlFor="state-select" className="text-xs text-gray-300">Target State:</label>
                <select
                  id="state-select"
                  value={stateOverride}
                  onChange={e => setStateOverride(e.target.value)}
                  className="bg-[#282828] hover:bg-[#323232] border border-white/20 hover:border-white/40 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#ff4e3a] focus:border-[#ff4e3a] transition-all cursor-pointer"
                >
                  <option value="">Auto-Detect from Document</option>
                  {SUPPORTED_STATES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Selection Controls */}
          {documents.length > 0 && (
            <div className="flex items-center justify-between mb-3 text-xs text-gray-400">
              <span>{documents.length} document{documents.length === 1 ? '' : 's'} available in workspace</span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedIds(documents.map(d => d.doc_id))}
                  className="flex items-center gap-1 text-gray-300 hover:text-white underline text-[11px]"
                >
                  <CheckSquare className="w-3 h-3 text-[#ff4e3a]" />
                  <span>Select All</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedIds([])}
                  className="flex items-center gap-1 text-gray-400 hover:text-white underline text-[11px]"
                >
                  <Square className="w-3 h-3" />
                  <span>Deselect All</span>
                </button>
              </div>
            </div>
          )}

          {/* Document Pills */}
          {documents.length === 0 ? (
            <div className="p-8 text-center border-2 border-dashed border-white/10 rounded-lg">
              <Upload className="w-8 h-8 mx-auto mb-2 text-gray-500" />
              <p className="text-sm text-gray-300 font-medium">No documents uploaded yet</p>
              <p className="text-xs text-gray-500 mt-1">Upload your Sale Deed, Allotment Letter, or Brochure (PDF, TXT, DOCX) to begin due diligence.</p>
              {onUpload && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-4 inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-4 py-2 text-xs font-semibold rounded transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Choose Documents (PDF/TXT)</span>
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
              {documents.map((doc, idx) => {
                const checked = selectedIds.includes(doc.doc_id);
                return (
                  <label
                    key={doc.doc_id}
                    className={`flex items-start gap-3 p-3.5 rounded border cursor-pointer transition-colors ${
                      checked ? 'bg-[#ff4e3a]/10 border-[#ff4e3a]' : 'bg-[#242424] border-white/10 hover:border-white/30'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={e => {
                        if (e.target.checked) setSelectedIds(ids => [...ids, doc.doc_id]);
                        else setSelectedIds(ids => ids.filter(id => id !== doc.doc_id));
                      }}
                      className="mt-1 rounded accent-[#ff4e3a]"
                    />
                    <div className="overflow-hidden flex-1">
                      <p className="text-xs font-semibold text-white truncate" title={doc.filename}>{doc.filename}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-gray-400">
                          Doc #{idx + 1} · {doc.num_chunks} chunks
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            className="text-[10px] underline text-gray-400 hover:text-white"
                            onClick={(e) => {
                              e.preventDefault();
                              void onOpenDoc(doc);
                            }}
                          >
                            View
                          </button>
                          {onRemoveDoc && (
                            <button
                              type="button"
                              className="text-[10px] text-red-400 hover:text-red-300 flex items-center gap-0.5"
                              title="Remove document"
                              onClick={(e) => {
                                e.preventDefault();
                                setSelectedIds(ids => ids.filter(id => id !== doc.doc_id));
                                void onRemoveDoc(doc.doc_id);
                              }}
                            >
                              <Trash2 className="w-2.5 h-2.5" />
                              <span>Remove</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">
              {selectedIds.length} document{selectedIds.length === 1 ? '' : 's'} selected
            </span>
            <button
              onClick={runDueDiligence}
              disabled={loading || selectedIds.length === 0 || busy}
              className="flex items-center gap-2 bg-white text-[#121212] hover:bg-gray-200 px-5 py-2.5 text-xs font-bold uppercase tracking-wider rounded transition-all disabled:opacity-40"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin text-[#ff4e3a]" /> : <RefreshCw className="w-4 h-4" />}
              <span>{loading ? 'Analyzing Property Documents…' : 'Run Due-Diligence'}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-950/60 border border-red-500/50 p-4 rounded mb-8 text-sm text-red-200 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Report Output */}
        {report && (
          <div className="space-y-8 animate-fadeIn">
            {/* Overview Banner */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-[#1a1a1a] border border-white/10 p-6 rounded-lg">
              {/* Score Tile */}
              <div className="flex flex-col justify-center items-center p-6 bg-[#242424] rounded-md text-center border border-white/5">
                <span className="text-xs uppercase tracking-wider text-gray-400 mb-1 font-mono">
                  PropCheck Index
                </span>
                <span className={`text-5xl font-black ${
                  report.overall_score >= 80 ? 'text-emerald-400' : report.overall_score >= 50 ? 'text-amber-400' : 'text-[#ff4e3a]'
                }`}>
                  {report.overall_score}
                  <span className="text-xl text-gray-400 font-normal">/100</span>
                </span>
                <span className={`mt-2 px-2.5 py-1 text-[11px] font-bold rounded uppercase tracking-wider ${
                  report.overall_score >= 80 ? 'bg-emerald-500/20 text-emerald-300' : report.overall_score >= 50 ? 'bg-amber-500/20 text-amber-300' : 'bg-red-500/20 text-red-300'
                }`}>
                  {report.risk_category.replace(/_/g, ' ')}
                </span>
              </div>

              {/* Property Details */}
              <div className="md:col-span-2 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-white/10 text-xs font-mono rounded text-gray-300">
                      State: {report.state_confirmed}
                    </span>
                    <span className="px-2 py-0.5 bg-white/10 text-xs font-mono rounded text-gray-300">
                      Unit: {report.unit_identifier}
                    </span>
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">{report.property_name}</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">{report.summary}</p>
                </div>

                <div className="text-xs text-gray-500 mt-4 pt-4 border-t border-white/10">
                  {report.documents_analyzed.length} documents analyzed · {report.cross_document_findings.length} verification checks evaluated
                </div>
              </div>
            </div>

            {/* Official RERA Verification Section */}
            <div className="bg-[#1a1a1a] border border-white/10 p-6 rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-bold text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-[#ff4e3a]" />
                  <span>Official RERA Verification Status</span>
                </h4>
              </div>

              {report.rera_verification.length === 0 ? (
                <div className="p-4 bg-amber-950/30 border border-amber-500/30 rounded text-sm text-amber-200">
                  <AlertTriangle className="w-4 h-4 inline mr-2 text-amber-400" />
                  No RERA registration number was detected in the submitted documents. Under Section 3 of the Real Estate (Regulation and Development) Act 2016, projects exceeding 500 sq.m or 8 units must be officially registered.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.rera_verification.map((r, idx) => (
                    <div key={idx} className="bg-[#242424] border border-white/10 p-4 rounded-md">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono bg-[#ff4e3a]/20 text-[#ff4e3a] px-2 py-0.5 rounded font-bold">
                          {r.authority}
                        </span>
                        <span className={`text-[11px] px-2 py-0.5 rounded font-semibold ${
                          r.status === 'VERIFIED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : r.status === 'FORMAT_VALID_OFFLINE_VERIFICATION_PENDING'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : r.status === 'INVALID_FORMAT'
                            ? 'bg-red-500/20 text-red-300'
                            : 'bg-blue-500/20 text-blue-300'
                        }`}>
                          {r.status === 'FORMAT_VALID_OFFLINE_VERIFICATION_PENDING'
                            ? 'Format Valid · Portal Verification Required'
                            : r.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-base font-mono font-bold text-white">{r.registration_number}</p>
                      <p className="text-xs text-gray-300 mt-2">{r.status_message}</p>
                      
                      <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between">
                        <a
                          href={r.official_search_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-[#ff4e3a] hover:underline flex items-center gap-1 font-semibold"
                        >
                          <span>Verify on Official {r.authority} Portal</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Cross-Document Consistency Matrix */}
            <div className="bg-[#1a1a1a] border border-white/10 p-6 rounded-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                  <h4 className="text-lg font-bold text-white">Cross-Document Consistency Findings</h4>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Deterministic comparison across carpet area, land parcel, unit ID, and financial consideration.
                  </p>
                </div>

                {/* Filter buttons */}
                <div className="flex gap-2 flex-wrap text-xs">
                  {[
                    { id: 'ALL', label: 'All Findings' },
                    { id: 'CRITICAL_HIGH', label: 'Discrepancies' },
                    { id: 'PASS', label: 'Verified Matches' },
                  ].map(f => (
                    <button
                      key={f.id}
                      onClick={() => setFilterSeverity(f.id)}
                      className={`px-3 py-1.5 rounded transition-all font-semibold ${
                        filterSeverity === f.id
                          ? 'bg-[#ff4e3a] text-white'
                          : 'bg-[#282828] text-gray-300 hover:bg-[#333]'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>

              {filteredFindings.length === 0 ? (
                <p className="text-sm text-gray-400 italic">No findings matching current filter.</p>
              ) : (
                <div className="space-y-4">
                  {filteredFindings.map((finding) => {
                    const isCrit = finding.severity === 'CRITICAL';
                    const isHigh = finding.severity === 'HIGH';
                    const isPass = finding.severity === 'PASS';
                    const isInfo = finding.severity === 'INFO';

                    return (
                      <div
                        key={finding.finding_id}
                        className={`p-5 rounded-md border ${
                          isCrit
                            ? 'bg-red-950/20 border-red-500/40'
                            : isHigh
                            ? 'bg-amber-950/20 border-amber-500/40'
                            : isPass
                            ? 'bg-emerald-950/20 border-emerald-500/30'
                            : isInfo
                            ? 'bg-blue-950/20 border-blue-500/30'
                            : 'bg-[#242424] border-white/10'
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            {isPass ? (
                              <CheckCircle className="w-4 h-4 text-emerald-400" />
                            ) : isCrit ? (
                              <AlertCircle className="w-4 h-4 text-red-400" />
                            ) : (
                              <AlertTriangle className="w-4 h-4 text-amber-400" />
                            )}
                            <h5 className="font-bold text-white text-sm">{finding.title}</h5>
                          </div>
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded tracking-wider ${
                            isCrit ? 'bg-red-500/30 text-red-300' : isHigh ? 'bg-amber-500/30 text-amber-300' : isPass ? 'bg-emerald-500/30 text-emerald-300' : 'bg-blue-500/30 text-blue-300'
                          }`}>
                            {finding.severity} · {finding.status.replace(/_/g, ' ')}
                          </span>
                        </div>

                        <p className="text-xs text-gray-300 leading-relaxed mb-3">
                          {finding.explanation}
                        </p>

                        {/* Values compared */}
                        {(finding.doc1_value || finding.doc2_value) && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-black/40 p-3 rounded-lg font-mono mb-3 border border-white/5">
                            <div className="text-gray-300 truncate">
                              <span className="text-gray-400 block text-[10px] uppercase tracking-wider mb-1">
                                {finding.doc1_name || 'Document 1'}:
                              </span>
                              <span className="font-bold text-white text-sm">{finding.doc1_value || 'Not stated'}</span>
                            </div>
                            <div className="text-gray-300 truncate">
                              <span className="text-gray-400 block text-[10px] uppercase tracking-wider mb-1">
                                {finding.doc2_name || 'Document 2'}:
                              </span>
                              <span className="font-bold text-white text-sm">{finding.doc2_value || 'Not stated'}</span>
                            </div>
                          </div>
                        )}

                        {/* Excerpts / Supporting Evidence Quotes */}
                        {(finding.doc1_excerpt || finding.doc2_excerpt) && (
                          <div className="text-[11px] text-gray-300 bg-black/25 p-3 rounded-lg mb-3 border-l-2 border-[#ff4e3a]/60 space-y-1.5">
                            {finding.doc1_excerpt && (
                              <div>
                                <span className="text-gray-400 font-mono text-[10px] uppercase font-bold mr-2">{finding.doc1_name}:</span>
                                <span className="italic text-gray-200 leading-relaxed">&ldquo;{finding.doc1_excerpt}&rdquo;</span>
                              </div>
                            )}
                            {finding.doc2_excerpt && (
                              <div>
                                <span className="text-gray-400 font-mono text-[10px] uppercase font-bold mr-2">{finding.doc2_name}:</span>
                                <span className="italic text-gray-200 leading-relaxed">&ldquo;{finding.doc2_excerpt}&rdquo;</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Actionable next step and inspection buttons */}
                        <div className="text-xs text-gray-300 bg-white/5 p-3.5 rounded-lg border border-white/10 flex flex-col md:flex-row md:items-start justify-between gap-4">
                          <div className="flex-1">
                            <span className="text-[#ff4e3a] font-bold text-xs uppercase tracking-wide block mb-1.5 font-mono">Recommended Homebuyer Action:</span>
                            <p className="text-gray-200 leading-relaxed">{finding.actionable_next_step}</p>
                          </div>

                          <div className="flex flex-wrap items-center gap-2 shrink-0">
                            {finding.doc1_id && (
                              <button
                                type="button"
                                className="text-xs font-semibold px-2.5 py-1.5 rounded bg-[#ff4e3a]/20 text-[#ff4e3a] hover:bg-[#ff4e3a]/30 border border-[#ff4e3a]/40 transition-colors flex items-center gap-1"
                                onClick={() => onSource({
                                  docId: finding.doc1_id,
                                  location: {
                                    chunk_id: 'c00000',
                                    page: finding.doc1_page ?? 1,
                                    section_id: finding.category || 'Property Evidence',
                                    start: finding.doc1_start ?? 0,
                                    end: finding.doc1_end ?? (finding.doc1_excerpt?.length || 50),
                                    page_start: finding.doc1_start ?? 0,
                                    page_end: finding.doc1_end ?? (finding.doc1_excerpt?.length || 50),
                                    ocr: false,
                                  },
                                  quote: finding.doc1_excerpt || finding.doc1_value || finding.title,
                                })}
                              >
                                <span>Inspect in {finding.doc1_name}</span>
                              </button>
                            )}

                            {finding.doc2_id && finding.doc2_id !== finding.doc1_id && (
                              <button
                                type="button"
                                className="text-xs font-semibold px-2.5 py-1.5 rounded bg-white/10 text-gray-200 hover:bg-white/20 border border-white/20 transition-colors flex items-center gap-1"
                                onClick={() => onSource({
                                  docId: finding.doc2_id,
                                  location: {
                                    chunk_id: 'c00000',
                                    page: finding.doc2_page ?? 1,
                                    section_id: finding.category || 'Property Evidence',
                                    start: finding.doc2_start ?? 0,
                                    end: finding.doc2_end ?? (finding.doc2_excerpt?.length || 50),
                                    page_start: finding.doc2_start ?? 0,
                                    page_end: finding.doc2_end ?? (finding.doc2_excerpt?.length || 50),
                                    ocr: false,
                                  },
                                  quote: finding.doc2_excerpt || finding.doc2_value || finding.title,
                                })}
                              >
                                <span>Inspect in {finding.doc2_name}</span>
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Action Checklist for Homebuyer */}
            <div className="bg-[#1a1a1a] border border-white/10 p-6 rounded-lg">
              <h4 className="text-lg font-bold text-white mb-1">Due-Diligence Action Checklist</h4>
              <p className="text-xs text-gray-400 mb-4">
                Recommended physical and legal verification steps before financial commitment.
              </p>
              <div className="space-y-2.5">
                {report.homebuyer_action_checklist.map((item, idx) => (
                  <label key={idx} className="flex items-start gap-3 p-3 bg-[#242424] rounded border border-white/5 text-xs text-gray-300 cursor-pointer hover:bg-[#2c2c2c]">
                    <input type="checkbox" className="mt-0.5 rounded accent-[#ff4e3a]" />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Disclaimer */}
            <div className="p-4 bg-white/5 border border-white/10 rounded text-[11px] text-gray-400 leading-relaxed font-mono">
              <strong className="text-gray-300 block mb-1">LEGAL NOTICE & LIMITATIONS:</strong>
              {report.disclaimer}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
