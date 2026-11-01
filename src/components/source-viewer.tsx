'use client';

import { useEffect, useRef, useState } from 'react';
import type { PDFDocumentProxy, RenderTask, TextLayer } from 'pdfjs-dist';
import { api } from '@/lib/api';
import { SourceDocument, SourceSelection } from '@/lib/audit-contracts';
import { markPdfText, normalizedPositions, sourceSlice } from '@/lib/source-highlight';
import { LegalNotice } from './legal-notice';

interface Props { selection: SourceSelection; onClose: () => void }

export function SourceViewer({ selection, onClose }: Props) {
  const [source, setSource] = useState<SourceDocument | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('Loading source…');
  const [activePage, setActivePage] = useState<SourceDocument['pages'][0] | null>(null);
  const [activeRange, setActiveRange] = useState<[number, number]>([selection.location.page_start, selection.location.page_end]);
  const canvas = useRef<HTMLCanvasElement>(null);
  const layer = useRef<HTMLDivElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const location = selection.location;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab') {
        const nodes = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, a[href], summary, [tabindex="0"]') || []);
        const first = nodes[0], last = nodes.at(-1);
        if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('keydown', key); previous?.focus(); };
  }, [onClose]);

  useEffect(() => {
    if (!source) return;
    const timer = setTimeout(onClose, Math.max(0, source.metadata.expires_at * 1000 - Date.now()));
    return () => clearTimeout(timer);
  }, [source, onClose]);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    setSource(null); setError(''); setNotice('Loading source…');
    setActivePage(null);
    let pdf: PDFDocumentProxy | undefined;
    let render: RenderTask | undefined;
    let textLayer: TextLayer | undefined;
    const host = layer.current;
    const marks = overlay.current;
    host?.replaceChildren(); marks?.replaceChildren();

    async function load() {
      const record = await api.source(selection.docId);
      if (disposed) return;
      setSource(record);

      if (!record.pages || record.pages.length === 0) {
        setNotice('No extracted text available for this document.');
        return;
      }

      // 1. Locate current page safely
      let currentPage = record.pages.find(item => item.page === location.page);
      if (!currentPage) {
        currentPage = record.pages.find(item => item.page === 1) || record.pages[0];
      }

      // 2. Resolve character offsets safely with quote matching
      let resolvedStart = location.page_start;
      let resolvedEnd = location.page_end;
      const targetQuote = selection.quote?.trim();

      if (targetQuote) {
        // Direct search on currentPage
        const directIdx = currentPage.text.indexOf(targetQuote);
        if (directIdx !== -1) {
          resolvedStart = Array.from(currentPage.text.slice(0, directIdx)).length;
          resolvedEnd = resolvedStart + Array.from(targetQuote).length;
        } else {
          // Case-insensitive search on currentPage
          const lowerPage = currentPage.text.toLowerCase();
          const lowerQuote = targetQuote.toLowerCase();
          const lowerIdx = lowerPage.indexOf(lowerQuote);
          if (lowerIdx !== -1) {
            resolvedStart = Array.from(currentPage.text.slice(0, lowerIdx)).length;
            resolvedEnd = resolvedStart + Array.from(targetQuote).length;
          } else {
            // Search other pages in record
            for (const p of record.pages) {
              const pLower = p.text.toLowerCase();
              const pIdx = pLower.indexOf(lowerQuote);
              if (pIdx !== -1) {
                currentPage = p;
                resolvedStart = Array.from(p.text.slice(0, pIdx)).length;
                resolvedEnd = resolvedStart + Array.from(targetQuote).length;
                break;
              }
            }
          }
        }
      }

      const pageTextChars = Array.from(currentPage.text);
      const pageLen = pageTextChars.length;
      if (resolvedStart < 0 || resolvedStart >= pageLen) {
        resolvedStart = 0;
      }
      if (resolvedEnd <= resolvedStart || resolvedEnd > pageLen) {
        resolvedEnd = Math.min(pageLen, resolvedStart + Math.min(60, pageLen));
      }

      setActivePage(currentPage);
      setActiveRange([resolvedStart, resolvedEnd]);

      // If document is not a PDF or has no visual page number, show canonical extracted text notice
      if (!record.metadata.has_pdf || currentPage.page === null) {
        setNotice('Highlighted in canonical extracted text.');
        return;
      }

      // Try rendering the original PDF
      try {
        const pdfjs = await import('pdfjs-dist');
        pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
        const data = await api.pdf(selection.docId, controller.signal);
        if (disposed) return;
        pdf = await pdfjs.getDocument({ data, isEvalSupported: false, disableFontFace: true }).promise;
        if (disposed) { await pdf.destroy(); return; }
        const pageNum = currentPage.page || 1;
        const pdfPage = await pdf.getPage(pageNum);
        const base = pdfPage.getViewport({ scale: 1 });
        const scale = Math.min(1.5, 800 / base.width);
        const viewport = pdfPage.getViewport({ scale });
        const element = canvas.current;
        if (!element || !host || !marks || disposed) return;
        element.width = viewport.width; element.height = viewport.height;
        element.style.width = `${viewport.width}px`; element.style.height = `${viewport.height}px`;
        host.style.setProperty('--scale-factor', String(scale));
        host.style.setProperty('--total-scale-factor', String(scale));
        host.style.width = `${viewport.width}px`; host.style.height = `${viewport.height}px`;
        render = pdfPage.render({ canvas: element, viewport });
        await render.promise;
        if (disposed) return;
        const addMark = (left: number, top: number, width: number, height: number) => {
          const mark = document.createElement('span');
          mark.className = 'source-mark';
          Object.assign(mark.style, { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` });
          marks.appendChild(mark);
        };
        if (currentPage.ocr) {
          const words = currentPage.words.filter(word => word.start < resolvedEnd && word.end > resolvedStart);
          words.forEach(word => addMark(word.box[0] * viewport.width, word.box[1] * viewport.height, word.box[2] * viewport.width, word.box[3] * viewport.height));
          setNotice(words.length ? 'OCR word locations highlighted. Verify recognition against the image.' : 'OCR location could not be highlighted; use the extracted text below.');
        } else {
          textLayer = new pdfjs.TextLayer({ textContentSource: await pdfPage.getTextContent(), container: host, viewport });
          await textLayer.render();
          if (disposed) return;
          const selectedText = sourceSlice(currentPage.text, resolvedStart, resolvedEnd);
          const needle = normalizedPositions(selectedText).text;
          const prefix = normalizedPositions(sourceSlice(currentPage.text, 0, resolvedStart)).text;
          const occurrence = needle ? prefix.split(needle).length - 1 : 0;
          const boxes = markPdfText(host, selectedText, currentPage.text, occurrence);
          const bounds = host.getBoundingClientRect();
          boxes.forEach(box => addMark(box.left - bounds.left, box.top - bounds.top, box.width, box.height));
          setNotice(boxes.length ? 'Matched quotation highlighted on the original PDF.' : 'Highlighted in canonical extracted text below. (Original PDF layout differs from extracted text stream)');
        }
      } catch {
        if (!disposed) {
          setNotice('PDF rendering unavailable in this view; verify using the canonical extracted text passage below.');
        }
      }
    }

    void load().catch(failure => {
      if (!disposed) {
        setError(failure instanceof Error ? failure.message : 'Source could not be loaded.');
        setNotice('');
      }
    });

    return () => {
      disposed = true; controller.abort(); render?.cancel(); textLayer?.cancel();
      if (pdf) void pdf.destroy();
      host?.replaceChildren(); marks?.replaceChildren();
    };
  }, [selection.docId, location.page, location.page_start, location.page_end, selection.quote]);

  const renderedPage = activePage || source?.pages.find(item => item.page === location.page) || source?.pages[0];
  const [startIdx, endIdx] = activeRange;
  const quote = renderedPage && endIdx > startIdx ? sourceSlice(renderedPage.text, startIdx, endIdx) : selection.quote;

  return <div ref={dialog} className="fixed inset-0 z-[90] bg-black/70 p-3 md:p-8 overflow-auto" role="dialog" aria-modal="true" aria-label="Document source viewer">
    <div className="max-w-5xl mx-auto bg-[#f4ead4] text-[#151515] p-5 md:p-8 rounded-2xl border border-black/10 shadow-2xl">
      <div className="flex justify-between items-center gap-4 border-b border-black/10 pb-3">
        <h2 className="text-xl font-bold">{source?.metadata.filename || 'Document source'}</h2>
        <button ref={close} onClick={onClose} className="text-sm underline font-semibold hover:text-[#ff4e3a] transition-colors">Close source</button>
      </div>
      <p className="text-xs my-3 text-neutral-700">
        {renderedPage?.page ? `Page ${renderedPage.page} · ` : ''}
        {location.section_id || 'Property Evidence'} · characters {startIdx}–{endIdx} (extracted text)
      </p>
      {notice && <p role="status" className="text-sm mb-4 font-medium text-emerald-800">{notice}</p>}
      {error && <p role="alert" className="text-red-800 mb-4 font-medium">{error}</p>}
      <div className={`${source?.metadata.has_pdf ? '' : 'hidden'} overflow-auto max-h-[65vh] border border-black/15 rounded-xl bg-neutral-100`}>
        <div className="relative w-fit"><canvas ref={canvas} aria-label="Original PDF page" /><div ref={layer} className="pdf-text-layer" /><div ref={overlay} className="absolute inset-0 pointer-events-none" /></div>
      </div>
      {renderedPage && (
        <details open className="mt-5 bg-black/5 p-4 rounded-xl border border-black/10">
          <summary className="cursor-pointer text-sm font-bold">Canonical extracted passage</summary>
          <pre className="whitespace-pre-wrap text-sm leading-relaxed mt-3 max-h-64 overflow-auto font-mono bg-white p-3 rounded-lg border border-black/10 text-neutral-900">
            {sourceSlice(renderedPage.text, Math.max(0, startIdx - 140), startIdx)}
            <mark className="bg-yellow-300 text-black font-bold px-1 rounded shadow-sm">{quote}</mark>
            {sourceSlice(renderedPage.text, endIdx, endIdx + 140)}
          </pre>
        </details>
      )}
      <div className="mt-4">
        <LegalNotice />
      </div>
    </div>
  </div>;
}
