import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { api } from '@/lib/api';
import { doc } from '@/test/fixtures';
import { PropCheckDashboard } from './propcheck-dashboard';
import { PropertyDueDiligenceReport } from '@/lib/property-contracts';

const mockReport: PropertyDueDiligenceReport = {
  property_name: 'Godrej Woods',
  unit_identifier: 'Flat 402',
  detected_state: 'Maharashtra',
  state_confirmed: 'Maharashtra',
  overall_score: 85,
  risk_category: 'LOW_RISK',
  summary: 'Documentation shows good consistency.',
  documents_analyzed: [
    { doc_id: doc.doc_id, filename: doc.filename },
    { doc_id: 'd2', filename: 'allotment.pdf' },
  ],
  rera_verification: [
    {
      registration_number: 'P51800000001',
      project_name: 'Godrej Woods',
      promoter_name: 'Godrej Properties',
      state: 'Maharashtra',
      authority: 'MahaRERA',
      status: 'FORMAT_VALID_OFFLINE_VERIFICATION_PENDING',
      status_message: 'Format verified.',
      verified_at: 1000,
      official_portal_url: 'https://maharera.maharashtra.gov.in',
      official_search_url: 'https://maharera.maharashtra.gov.in/search',
      evidence: [],
      disclaimer: 'Verify on official portal.',
    },
  ],
  cross_document_findings: [
    {
      finding_id: 'F-1',
      title: 'Carpet Area Consistent',
      category: 'AREA',
      severity: 'PASS',
      status: 'MATCHED',
      explanation: 'Carpet area matches across both deeds.',
      doc1_id: doc.doc_id,
      doc1_name: doc.filename,
      doc1_value: '1050 sq.ft',
      doc2_id: 'd2',
      doc2_name: 'allotment.pdf',
      doc2_value: '1050 sq.ft',
      actionable_next_step: 'Retain approved floor plans.',
    },
  ],
  extracted_factsheets: [],
  homebuyer_action_checklist: ['Check encumbrance certificate at SRO.'],
  disclaimer: 'Informational only.',
  generated_at: 1000,
};

it('renders empty documents message when no documents available', () => {
  render(<PropCheckDashboard documents={[]} busy={false} onSource={vi.fn()} onOpenDoc={vi.fn()} />);
  expect(screen.getByText(/No documents uploaded yet/)).toBeVisible();
});

it('allows selecting documents and running due-diligence report', async () => {
  const secondDoc = { ...doc, doc_id: 'd2', filename: 'allotment.pdf' };
  const mockApi = vi.spyOn(api, 'propertyDueDiligence').mockResolvedValue(mockReport);

  render(<PropCheckDashboard documents={[doc, secondDoc]} busy={false} onSource={vi.fn()} onOpenDoc={vi.fn()} />);
  expect(screen.getByText(doc.filename)).toBeVisible();
  expect(screen.getByText('allotment.pdf')).toBeVisible();

  // Select both documents
  const checkboxes = screen.getAllByRole('checkbox');
  fireEvent.click(checkboxes[0]);
  fireEvent.click(checkboxes[1]);

  // Click Run Due-Diligence
  const runBtn = screen.getByRole('button', { name: /Run Due-Diligence/i });
  expect(runBtn).toBeEnabled();
  fireEvent.click(runBtn);

  // Expect report rendered
  await waitFor(() => {
    expect(screen.getByText('Godrej Woods')).toBeVisible();
    expect(screen.getByText('P51800000001')).toBeVisible();
    expect(screen.getByText('Carpet Area Consistent')).toBeVisible();
    expect(screen.getByText(/Check encumbrance certificate/)).toBeVisible();
  });

  expect(mockApi).toHaveBeenCalledWith([doc.doc_id, secondDoc.doc_id], undefined);
});

it('renders inspection buttons for both documents and calls onSource with exact offsets', async () => {
  const discrepancyReport: PropertyDueDiligenceReport = {
    ...mockReport,
    cross_document_findings: [
      {
        finding_id: 'DISC-FIN-1',
        title: 'Agreement Consideration Amount Mismatch',
        category: 'FINANCIAL',
        severity: 'HIGH',
        status: 'CONFIRMED_MISMATCH',
        explanation: 'Consideration differs: ₹95,00,000 in agreement.pdf vs ₹99,00,000 in brochure.pdf.',
        doc1_id: 'doc-agreement',
        doc1_name: 'agreement.pdf',
        doc1_value: '₹95,00,000',
        doc1_excerpt: 'total sale consideration of Rs. 95,00,000',
        doc1_page: 1,
        doc1_start: 120,
        doc1_end: 161,
        doc2_id: 'doc-brochure',
        doc2_name: 'brochure.pdf',
        doc2_value: '₹99,00,000',
        doc2_excerpt: 'starting consideration from Rs. 99,00,000',
        doc2_page: 1,
        doc2_start: 85,
        doc2_end: 126,
        actionable_next_step: 'Reconcile payment schedule.',
      },
    ],
  };

  const doc1 = { ...doc, doc_id: 'doc-agreement', filename: 'agreement.pdf' };
  const doc2 = { ...doc, doc_id: 'doc-brochure', filename: 'brochure.pdf' };
  vi.spyOn(api, 'propertyDueDiligence').mockResolvedValue(discrepancyReport);
  const onSource = vi.fn();

  render(<PropCheckDashboard documents={[doc1, doc2]} busy={false} onSource={onSource} onOpenDoc={vi.fn()} />);

  const checkboxes = screen.getAllByRole('checkbox');
  fireEvent.click(checkboxes[0]);
  fireEvent.click(checkboxes[1]);
  fireEvent.click(screen.getByRole('button', { name: /Run Due-Diligence/i }));

  await waitFor(() => {
    expect(screen.getByText('Agreement Consideration Amount Mismatch')).toBeVisible();
  });

  const inspectDoc1 = screen.getByRole('button', { name: /Inspect in agreement\.pdf/i });
  const inspectDoc2 = screen.getByRole('button', { name: /Inspect in brochure\.pdf/i });
  expect(inspectDoc1).toBeVisible();
  expect(inspectDoc2).toBeVisible();

  fireEvent.click(inspectDoc1);
  expect(onSource).toHaveBeenCalledWith(expect.objectContaining({
    docId: 'doc-agreement',
    location: expect.objectContaining({
      page: 1,
      page_start: 120,
      page_end: 161,
    }),
    quote: 'total sale consideration of Rs. 95,00,000',
  }));

  fireEvent.click(inspectDoc2);
  expect(onSource).toHaveBeenCalledWith(expect.objectContaining({
    docId: 'doc-brochure',
    location: expect.objectContaining({
      page: 1,
      page_start: 85,
      page_end: 126,
    }),
    quote: 'starting consideration from Rs. 99,00,000',
  }));
});
