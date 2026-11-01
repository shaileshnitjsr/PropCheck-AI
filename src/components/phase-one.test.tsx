import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Audit, Location } from '@/lib/audit-contracts';
import { doc } from '@/test/fixtures';
import { api } from '@/lib/api';
import { AuditPanel } from './audit-panel';
import { SourceViewer } from './source-viewer';

const location: Location = { chunk_id: 'c1', page: null, section_id: '1.', start: 2, end: 6, page_start: 2, page_end: 6, ocr: false };
const audit: Audit = {
  doc_id: doc.doc_id, contract_type: 'lease', checklist: ['liability'], clauses: [{
    id: 'clause-1', type: 'Uncapped Liability', quoted_text: 'rent', chunk_id: 'c1', party: 'Tenant', confidence: 0.7, location,
    risk: { level: 'high', score: 80, why: 'Review exposure', rubric_id: 'v1' },
    redline: { original: 'rent', suggested: 'Proposed replacement', rationale: 'Review with counsel', disclaimer: 'Informational' },
  }], overall_risk: { level: 'high', score: 80, why: 'Maximum clause priority', rubric_id: 'v1' },
  summary: 'One located clause.', dropped_claims: 1, analyzed_chunks: 2, total_chunks: 2, rule_checks: [], warnings: ['Uncalibrated'], steps: ['verify'], disclaimer: 'Informational',
};

it('shows risk rationale, redline, coverage and clickable source without a fairness score', () => {
  const select = vi.fn();
  render(<AuditPanel result={audit} available busy={false} analyzing={false} onAnalyze={vi.fn()} onSource={select} />);
  expect(screen.getByText('HIGH · 80/100')).toBeInTheDocument();
  expect(screen.getByText('Review exposure')).toBeInTheDocument();
  expect(screen.getByText('Proposed replacement')).toBeInTheDocument();
  fireEvent.click(screen.getByText('View source · 1.'));
  expect(select).toHaveBeenCalledWith({ docId: doc.doc_id, location, quote: 'rent' });
  expect(screen.getByText(/Coverage: 2\/2/)).toBeInTheDocument();
});

it('highlights canonical text using Unicode code-point offsets and closes accessibly', async () => {
  vi.spyOn(api, 'source').mockResolvedValue({ metadata: doc, pages: [{ page: null, text: '😀 rent due', start: 0, ocr: false, words: [] }], chunks: [] });
  const close = vi.fn();
  render(<SourceViewer selection={{ docId: doc.doc_id, location, quote: 'rent' }} onClose={close} />);
  await waitFor(() => expect(screen.getByText('rent').tagName).toBe('MARK'));
  expect(screen.getByRole('status')).toHaveTextContent('canonical extracted text');
  fireEvent.keyDown(document, { key: 'Escape' });
  expect(close).toHaveBeenCalled();
});

it('reports expired sources without rendering a fabricated passage', async () => {
  vi.spyOn(api, 'source').mockRejectedValue(new Error('Document expired.'));
  render(<SourceViewer selection={{ docId: doc.doc_id, location, quote: 'rent' }} onClose={vi.fn()} />);
  expect(await screen.findByRole('alert')).toHaveTextContent('expired');
  expect(screen.queryByText('Canonical extracted passage')).not.toBeInTheDocument();
});
