'use client';

import { useRef, useState } from 'react';
import { FileText, Loader2, Upload } from 'lucide-react';
import { StoredDocument } from '@/lib/contracts';
import { generatePastedFilename } from '@/lib/paste-filename';

interface Props {
  document: StoredDocument | null;
  busy: boolean;
  onUpload: (fileOrFiles: File | File[]) => Promise<boolean>;
  status?: string;
  documents?: StoredDocument[];
}

export function UploadPanel({ document, busy, onUpload, status, documents }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [paste, setPaste] = useState('');
  const [dragging, setDragging] = useState(false);
  async function loadPaste() {
    if (!paste.trim()) return;
    const existingNames = (documents || []).map(d => d.filename);
    const filename = generatePastedFilename(paste.trim(), existingNames);
    if (await onUpload(new File([paste.trim()], filename, { type: 'text/plain' }))) setPaste('');
  }
  return <section id="upload" className="studio-section cream-theme">
    <p className="text-xs uppercase tracking-widest text-[#1d1c19]/60 mb-4 font-mono font-semibold">01 / Your document</p>
    <h2 className="heading-display text-4xl md:text-6xl mb-8">Upload & Understand</h2>
    <div className="grid md:grid-cols-2 gap-8 w-full">
      <div>
        <input ref={input} type="file" aria-label="Upload contract" className="sr-only"
          multiple
          accept=".pdf,application/pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.txt,text/plain,.md,text/markdown"
          disabled={busy}
          onChange={event => {
            const files = event.target.files ? Array.from(event.target.files) : [];
            if (files.length > 0) void onUpload(files);
            event.target.value = '';
          }} />
        <button type="button" disabled={busy} onClick={() => input.current?.click()}
          onDragOver={event => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={event => {
            event.preventDefault(); setDragging(false);
            const files = event.dataTransfer.files ? Array.from(event.dataTransfer.files) : [];
            if (files.length > 0 && !busy) void onUpload(files);
          }}
          className={`w-full border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer group shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral ${
            dragging
              ? 'border-coral bg-coral/10 scale-[0.99]'
              : 'border-[#1d1c19]/25 hover:border-coral bg-white/60 hover:bg-white/90'
          }`}>
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[#1d1c19]/5 group-hover:bg-coral/10 flex items-center justify-center transition-colors">
            {busy ? <Loader2 className="w-6 h-6 animate-spin text-coral" /> : <Upload className="w-6 h-6 text-[#1d1c19]/70 group-hover:text-coral transition-colors" />}
          </div>
          <span className="block font-semibold text-base text-[#1d1c19]" role="status">
            {busy ? (status || 'Processing…') : 'Drop property documents or choose files'}
          </span>
          <span className="block text-xs mt-2 text-[#1d1c19]/70">
            PDF, DOCX, TXT, MD · max 2 MiB per file · select one or multiple
          </span>
        </button>
        <p className="text-xs leading-relaxed mt-4 text-[#1d1c19]/70">
          Uploads, extracted text and vectors are retained until expiry or deletion. Local PII detection redacts detected entities before provider analysis; it can miss information. Browser history saves only document IDs and metadata.
        </p>
      </div>
      <div>
        <label htmlFor="paste-contract" className="block text-xs font-bold uppercase tracking-wider mb-2.5 text-[#1d1c19]">
          Or paste contract text
        </label>
        <textarea
          id="paste-contract"
          value={paste}
          onChange={event => setPaste(event.target.value)}
          maxLength={100000}
          disabled={busy}
          rows={7}
          placeholder="Paste agreement text, allotment clauses, or registration notes here…"
          className="w-full bg-white/80 hover:bg-white focus:bg-white border border-[#1d1c19]/25 focus:border-coral focus:ring-2 focus:ring-coral/20 rounded-xl p-4 text-sm resize-y outline-none transition-all placeholder:text-[#1d1c19]/45 text-[#1d1c19] shadow-sm"
        />
        <button type="button" disabled={busy || !paste.trim()} onClick={() => void loadPaste()} className="studio-btn mt-4">
          Load text
        </button>
      </div>
    </div>
    {document && (
      <div className="flex gap-3.5 items-start p-4 bg-white/70 border border-[#1d1c19]/20 rounded-xl shadow-sm mt-8 w-full" role="status">
        <div className="w-9 h-9 rounded-lg bg-coral/10 text-coral flex items-center justify-center shrink-0 mt-0.5">
          <FileText className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <strong className="block text-sm font-semibold truncate text-[#1d1c19]">{document.filename}</strong>
          <p className="text-xs text-[#1d1c19]/75 mt-1">
            {document.chars.toLocaleString()} characters · {document.num_chunks} {document.chunking_strategy} chunks · {document.ocr_pages} OCR pages · expires {new Date(document.expires_at * 1000).toLocaleString()}
          </p>
        </div>
      </div>
    )}
  </section>;
}
