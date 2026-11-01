import { describe, expect, it } from 'vitest';
import { extractMeaningfulTitle, generatePastedFilename } from './paste-filename';

describe('extractMeaningfulTitle', () => {
  it('extracts project name and document type from property registration certificates', () => {
    const text = `
      RAJASTHAN REAL ESTATE REGULATORY AUTHORITY
      FORM 'REP-III' REGISTRATION CERTIFICATE OF PROJECT
      Subject: Illustrative registration certificate for the fictional residential project “Aravali Heights”, stated to be situated on 4.25 acres in Jagatpura, Jaipur.
    `;
    expect(extractMeaningfulTitle(text)).toBe('Registration_Certificate_Aravali_Heights');
  });

  it('extracts project name and agreement type from agreements for sale', () => {
    const text = `
      Agreement for Sale
      Project Name: Green Valley Residency
      Developer: Sunrise Homes Private Limited
    `;
    expect(extractMeaningfulTitle(text)).toBe('Agreement_for_Sale_Green_Valley_Residency');
  });

  it('extracts allotment letter title and project name', () => {
    const text = `
      ALLOTMENT LETTER
      Subject: Allotment of Apartment in "Palm Greens Phase 1", Sector 150, Noida.
    `;
    expect(extractMeaningfulTitle(text)).toBe('Allotment_Letter_Palm_Greens_Phase_1');
  });

  it('returns null for generic contracts without property titles', () => {
    const text = 'This agreement is entered into on this day between Party A and Party B for consultancy services.';
    expect(extractMeaningfulTitle(text)).toBeNull();
  });
});

describe('generatePastedFilename', () => {
  it('generates meaningful filename for property documents and avoids collisions', () => {
    const text1 = 'Agreement for Sale for project Palm Greens. Consideration Rs. 50,00,000.';
    const fn1 = generatePastedFilename(text1, []);
    expect(fn1).toBe('Agreement_for_Sale_Palm_Greens.txt');

    const fn2 = generatePastedFilename(text1, [fn1]);
    expect(fn2).toBe('Agreement_for_Sale_Palm_Greens_2.txt');

    const fn3 = generatePastedFilename(text1, [fn1, fn2]);
    expect(fn3).toBe('Agreement_for_Sale_Palm_Greens_3.txt');
  });

  it('generates sequential Pasted_Document_N.txt when text has no property title', () => {
    const genericText = 'General non-property terms and conditions text.';
    const fn1 = generatePastedFilename(genericText, []);
    expect(fn1).toBe('Pasted_Document_1.txt');

    const fn2 = generatePastedFilename(genericText, ['Pasted_Document_1.txt']);
    expect(fn2).toBe('Pasted_Document_2.txt');

    const fn3 = generatePastedFilename(genericText, ['Pasted_Document_1.txt', 'Pasted_Document_2.txt']);
    expect(fn3).toBe('Pasted_Document_3.txt');
  });

  it('handles existing pasted-document.txt and promotes to Pasted_Document_2.txt', () => {
    const genericText = 'General non-property terms and conditions text.';
    const fn = generatePastedFilename(genericText, ['pasted-document.txt']);
    expect(fn).toBe('Pasted_Document_2.txt');
  });
});
