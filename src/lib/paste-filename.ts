/**
 * Utility to generate unique, meaningful filenames for pasted contract/property text.
 */

export function extractMeaningfulTitle(text: string): string | null {
  if (!text || !text.trim()) return null;
  const sample = text.slice(0, 5000);

  // 1. Document Type Patterns
  let docType: string | null = null;
  const docTypePatterns: [RegExp, string][] = [
    [/\bAgreement\s+for\s+Sale\b/i, 'Agreement_for_Sale'],
    [/\bAllotment\s+Letter\b/i, 'Allotment_Letter'],
    [/\bRegistration\s+Certificate(?:\s+of\s+Project)?\b/i, 'Registration_Certificate'],
    [/\bSale\s+Deed\b/i, 'Sale_Deed'],
    [/\bConveyance\s+Deed\b/i, 'Conveyance_Deed'],
    [/\bLeave\s+(?:and|&)\s+Licen[sc]e(?:\s+Agreement)?\b/i, 'Leave_and_License'],
    [/\bLease\s+Agreement\b/i, 'Lease_Agreement'],
    [/\bProject\s+Brochure\b|\bBrochure\b/i, 'Brochure'],
    [/\bPossession\s+Letter\b/i, 'Possession_Letter'],
    [/\bTripartite\s+Agreement\b/i, 'Tripartite_Agreement'],
  ];
  for (const [pattern, name] of docTypePatterns) {
    if (pattern.test(sample)) {
      docType = name;
      break;
    }
  }

  // 2. Project Name Patterns
  let projectName: string | null = null;
  const projPatterns: RegExp[] = [
    /\b(?:Project\s+Name|Project)\s*[:\-–]\s*["']?([A-Za-z0-9\s&'-]{3,35}?)["']?(?:\r?\n|$|\s{2,})/i,
    /\b(?:known\s+as|project\s+named|project\s+called)\s+["'“]([A-Za-z0-9\s&'-]{3,35}?)["'”]/i,
    /\b(?:residential|commercial)?\s*project\s+["'“]([A-Za-z0-9\s&'-]{3,35}?)["'”]/i,
    /\b(?:Apartment\s+in|Flat\s+in|Unit\s+in|project\s+in)\s+["'“]([A-Za-z0-9\s&'-]{3,35}?)["'”]/i,
    /\b(?:residential\s+project|commercial\s+project|project\s+known\s+as|project)\s+([A-Z][A-Za-z0-9\s&'-]{3,30}?(?:Residency|Enclave|Gardens|Heights|Towers|Greens|Palms|Estate|City|Park|Villas|Square|Grande|Pratham))\b/i,
  ];
  for (const pattern of projPatterns) {
    const match = sample.match(pattern);
    if (match && match[1]) {
      const clean = match[1]
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/[\s-]+/g, '_');
      if (clean.length >= 3) {
        projectName = clean;
        break;
      }
    }
  }

  if (docType && projectName) return `${docType}_${projectName}`;
  if (projectName) return projectName;
  if (docType) return docType;
  return null;
}

export function generatePastedFilename(text: string, existingFilenames: string[] = []): string {
  const existingLower = new Set(existingFilenames.map(f => f.toLowerCase()));
  const title = extractMeaningfulTitle(text);

  if (title) {
    const base = `${title}.txt`;
    if (!existingLower.has(base.toLowerCase())) {
      return base;
    }
    let counter = 2;
    while (existingLower.has(`${title}_${counter}.txt`.toLowerCase())) {
      counter++;
    }
    return `${title}_${counter}.txt`;
  }

  let counter = 1;
  while (
    existingLower.has(`pasted_document_${counter}.txt`.toLowerCase()) ||
    (counter === 1 && existingLower.has('pasted-document.txt'))
  ) {
    counter++;
  }
  return `Pasted_Document_${counter}.txt`;
}
