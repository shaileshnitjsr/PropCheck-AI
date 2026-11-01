import { z } from 'zod';

export const reraResultSchema = z.object({
  registration_number: z.string(),
  project_name: z.string().nullable().optional(),
  promoter_name: z.string().nullable().optional(),
  state: z.string(),
  authority: z.string(),
  status: z.enum([
    'VERIFIED',
    'FORMAT_VALID_OFFLINE_VERIFICATION_PENDING',
    'UNABLE_TO_VERIFY',
    'NOT_FOUND',
    'INVALID_FORMAT',
    'NOT_APPLICABLE',
  ]),
  status_message: z.string(),
  verified_at: z.number(),
  valid_until: z.string().nullable().optional(),
  official_portal_url: z.string(),
  official_search_url: z.string(),
  evidence: z.array(z.string()).default([]),
  disclaimer: z.string(),
});

export const crossDocMismatchSchema = z.object({
  finding_id: z.string(),
  title: z.string(),
  category: z.string(),
  severity: z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'PASS']),
  status: z.string(),
  explanation: z.string(),
  doc1_id: z.string(),
  doc1_name: z.string(),
  doc1_value: z.string().nullable().optional(),
  doc1_excerpt: z.string().nullable().optional(),
  doc1_page: z.number().nullable().optional(),
  doc1_start: z.number().nullable().optional(),
  doc1_end: z.number().nullable().optional(),
  doc2_id: z.string(),
  doc2_name: z.string(),
  doc2_value: z.string().nullable().optional(),
  doc2_excerpt: z.string().nullable().optional(),
  doc2_page: z.number().nullable().optional(),
  doc2_start: z.number().nullable().optional(),
  doc2_end: z.number().nullable().optional(),
  actionable_next_step: z.string(),
});

export const propertyFactSheetSchema = z.object({
  doc_id: z.string(),
  filename: z.string(),
  detected_state: z.string(),
  state_confidence: z.number(),
  state_evidence: z.array(z.string()).default([]),
  project_name: z.string().nullable().optional(),
  developer_name: z.string().nullable().optional(),
  rera_records: z.array(reraResultSchema).default([]),
  identifiers: z.object({
    unit_flat_no: z.string().nullable().optional(),
    tower_wing: z.string().nullable().optional(),
    floor: z.string().nullable().optional(),
    survey_no: z.string().nullable().optional(),
    plot_no: z.string().nullable().optional(),
    khasra_no: z.string().nullable().optional(),
  }).passthrough(),
  areas: z.object({
    carpet_area_sqft: z.number().nullable().optional(),
    built_up_area_sqft: z.number().nullable().optional(),
    super_built_up_area_sqft: z.number().nullable().optional(),
  }).passthrough(),
  financials: z.object({
    agreement_value_inr: z.number().nullable().optional(),
    booking_amount_inr: z.number().nullable().optional(),
  }).passthrough(),
  dates: z.object({
    agreement_date: z.string().nullable().optional(),
    possession_date: z.string().nullable().optional(),
    grace_period_months: z.number().nullable().optional(),
  }).passthrough(),
  parties: z.object({
    buyers: z.array(z.string()).default([]),
    sellers_promoters: z.array(z.string()).default([]),
  }).passthrough(),
  extracted_at: z.number(),
});

export const propertyDueDiligenceReportSchema = z.object({
  property_name: z.string(),
  unit_identifier: z.string(),
  detected_state: z.string(),
  state_confirmed: z.string(),
  overall_score: z.number(),
  risk_category: z.enum(['LOW_RISK', 'MODERATE_ATTENTION', 'HIGH_RISK_DISCREPANCY']),
  summary: z.string(),
  documents_analyzed: z.array(z.object({
    doc_id: z.string(),
    filename: z.string(),
  })),
  rera_verification: z.array(reraResultSchema),
  cross_document_findings: z.array(crossDocMismatchSchema),
  extracted_factsheets: z.array(propertyFactSheetSchema).default([]),
  homebuyer_action_checklist: z.array(z.string()),
  disclaimer: z.string(),
  generated_at: z.number(),
});

export type RERAResult = z.infer<typeof reraResultSchema>;
export type CrossDocMismatch = z.infer<typeof crossDocMismatchSchema>;
export type PropertyFactSheet = z.infer<typeof propertyFactSheetSchema>;
export type PropertyDueDiligenceReport = z.infer<typeof propertyDueDiligenceReportSchema>;
