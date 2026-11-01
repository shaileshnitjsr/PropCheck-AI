import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { BenefitsPanel } from './benefits-panel';
import { ChatPanel } from './chat-panel';
import { AuditPanel } from './audit-panel';
import { UploadPanel } from './upload-panel';
import { StoredDocument } from '@/lib/contracts';

const sampleDoc: StoredDocument = {
  doc_id: '82f04be7-c250-44eb-97ac-65f24db6979c',
  filename: 'Sample_Agreement_For_Sale.txt',
  chars: 629,
  num_chunks: 1,
  created_at: 1793515544,
  expires_at: 1793519144,
  has_pdf: false,
  ocr_pages: 0,
  chunking_strategy: 'clause',
};

it('renders every party and finding, including later clauses, with click-to-quote', () => {
  const items = Array.from({ length: 14 }, (_, i) => ({
    party: `Party ${i % 3}`, benefit: `Finding ${i}`, kind: 'benefit' as const,
    clause: `Clause ${i}`, score: 7, chunk_ids: [`c${i}`],
  }));
  render(<BenefitsPanel result={{ items, analyzed_chunks: 20, total_chunks: 20, disclaimer: 'test' }} available busy={false} analyzing={false} onAnalyze={vi.fn()} />);
  expect(screen.getByText('Party 2')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Finding 13'));
  expect(screen.getByLabelText('Source quotation')).toHaveTextContent('Clause 13');
  expect(screen.getByText(/Informational only, not legal advice/)).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('20 / 20');
});

it('preserves source quotations and pages in chat', () => {
  render(<ChatPanel messages={[{ role: 'assistant', content: 'Answer [Excerpt 1]', sources: [{
    excerpt: 1, chunk_id: 'c0', preview: 'Original clause text', page: 3, distance: 0.1,
    section_id: '1.', start: 0, end: 20, page_start: 0, page_end: 20, ocr: false,
  }] }]} available busy={false} sending={false} onSend={vi.fn()} />);
  expect(screen.getByText('Excerpt 1 · Page 3 · c0')).toBeInTheDocument();
  expect(screen.getByText('Original clause text')).toBeInTheDocument();
});

it('keeps pasted text on a failed upload and clears it only on success', async () => {
  const upload = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
  render(<UploadPanel document={null} busy={false} onUpload={upload} />);
  const textarea = screen.getByLabelText('Or paste contract text');
  fireEvent.change(textarea, { target: { value: 'Private pasted contract' } });
  fireEvent.click(screen.getByRole('button', { name: 'Load text' }));
  await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
  expect(textarea).toHaveValue('Private pasted contract');
  fireEvent.click(screen.getByRole('button', { name: 'Load text' }));
  await waitFor(() => expect(textarea).toHaveValue(''));
});

it('assigns unique meaningful filenames to two distinct pasted documents', async () => {
  const uploadedFiles: File[] = [];
  const upload = vi.fn().mockImplementation(async (fileOrFiles: File | File[]) => {
    const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
    uploadedFiles.push(...files);
    return true;
  });

  const { rerender } = render(<UploadPanel document={null} busy={false} onUpload={upload} documents={[]} />);
  const textarea = screen.getByLabelText('Or paste contract text');

  // First paste: Aravali Heights
  fireEvent.change(textarea, { target: { value: 'Registration Certificate for project “Aravali Heights”' } });
  fireEvent.click(screen.getByRole('button', { name: 'Load text' }));
  await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
  expect(uploadedFiles[0].name).toBe('Registration_Certificate_Aravali_Heights.txt');

  // Second paste: Green Valley Residency
  rerender(<UploadPanel document={null} busy={false} onUpload={upload} documents={[{ ...sampleDoc, filename: uploadedFiles[0].name }]} />);
  fireEvent.change(textarea, { target: { value: 'Agreement for Sale for project “Green Valley Residency”' } });
  fireEvent.click(screen.getByRole('button', { name: 'Load text' }));
  await waitFor(() => expect(upload).toHaveBeenCalledTimes(2));
  expect(uploadedFiles[1].name).toBe('Agreement_for_Sale_Green_Valley_Residency.txt');
  expect(uploadedFiles[0].name).not.toEqual(uploadedFiles[1].name);
});

it('enables BenefitsPanel analysis when workspace document is available', () => {
  const onAnalyze = vi.fn().mockResolvedValue(undefined);
  render(
    <BenefitsPanel
      result={null}
      available={true}
      busy={false}
      analyzing={false}
      onAnalyze={onAnalyze}
      document={sampleDoc}
      documents={[sampleDoc]}
    />
  );
  expect(screen.getByText('Sample_Agreement_For_Sale.txt')).toBeInTheDocument();
  const btn = screen.getByRole('button', { name: 'Analyze document' });
  expect(btn).not.toBeDisabled();
  fireEvent.click(btn);
  expect(onAnalyze).toHaveBeenCalledTimes(1);
});

it('enables ChatPanel input and preset submission when workspace document is connected', async () => {
  const onSend = vi.fn().mockResolvedValue(true);
  render(
    <ChatPanel
      messages={[]}
      available={true}
      busy={false}
      sending={false}
      onSend={onSend}
      document={sampleDoc}
      documents={[sampleDoc]}
      docId={sampleDoc.doc_id}
    />
  );
  expect(screen.getByText('Sample_Agreement_For_Sale.txt')).toBeInTheDocument();
  const input = screen.getByPlaceholderText('Ask about a clause, obligation, or consequence…');
  expect(input).not.toBeDisabled();
  fireEvent.change(input, { target: { value: 'Who is the developer?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send question' }));
  expect(onSend).toHaveBeenCalledWith('Who is the developer?');
});

it('enables AuditPanel clause audit when workspace document is available', () => {
  const onAnalyze = vi.fn().mockResolvedValue(undefined);
  render(
    <AuditPanel
      result={null}
      available={true}
      busy={false}
      analyzing={false}
      onAnalyze={onAnalyze}
      onSource={vi.fn()}
      document={sampleDoc}
      documents={[sampleDoc]}
    />
  );
  expect(screen.getByText('Sample_Agreement_For_Sale.txt')).toBeInTheDocument();
  const btn = screen.getByRole('button', { name: 'Run clause audit' });
  expect(btn).not.toBeDisabled();
  fireEvent.click(btn);
  expect(onAnalyze).toHaveBeenCalledTimes(1);
});

it('shows clear upload prompt and disables actions when no document exists', () => {
  render(
    <BenefitsPanel
      result={null}
      available={false}
      busy={false}
      analyzing={false}
      onAnalyze={vi.fn()}
      document={null}
      documents={[]}
    />
  );
  expect(screen.getByText('Upload a document to begin.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Analyze document' })).toBeDisabled();
});
