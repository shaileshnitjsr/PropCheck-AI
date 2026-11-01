"""RERA Verifier Registry and Extractor."""

import re
from .base import BaseRERAAdapter, RERAResult, RERAStatus
from .maharera import MahaRERAAdapter
from .karnatakarera import KarnatakaRERAAdapter
from .uprera import UPRERAAdapter
from .haryanarera import HaryanaRERAAdapter
from .generic import GenericRERAAdapter

STATE_ADAPTERS: dict[str, type[BaseRERAAdapter]] = {
    "Maharashtra": MahaRERAAdapter,
    "Karnataka": KarnatakaRERAAdapter,
    "Uttar Pradesh": UPRERAAdapter,
    "Haryana": HaryanaRERAAdapter,
}

# Regex to detect RERA mentions in contract text
RERA_TEXT_REGEX = re.compile(
    r"(?i)\b(?:Maha|UP|K|H|TN|TS|Guj|Raj)?RERA\b[^\w\n]{0,35}?(?:(?:Reg(?:istration)?|No|Number|Certificate)[^\w\n]{0,15})?[:\-# ]*([A-Z0-9/\-]{5,35})\b|"
    r"\b(P5\d{8,11})\b|"
    r"\b(UPRERAPRJ\d{4,9})\b|"
    r"\b((?:PRM|ACK)/KA/RERA/[A-Z0-9/]+)\b|"
    r"\b(HRERA-[A-Z0-9\-]+)\b"
)


def get_verifier_for_state(state: str) -> BaseRERAAdapter:
    adapter_cls = STATE_ADAPTERS.get(state)
    if adapter_cls:
        return adapter_cls()
    return GenericRERAAdapter(state_name=state or "Unknown", authority_name=f"{state} RERA" if state else "State RERA")


def extract_rera_numbers(text: str) -> list[tuple[str, str]]:
    """Returns list of (registration_number, matched_excerpt)."""
    results: list[tuple[str, str]] = []
    seen = set()

    for match in RERA_TEXT_REGEX.finditer(text):
        groups = [g for g in match.groups() if g]
        if not groups:
            continue
        reg_no = groups[0].strip(" -#:")
        # Sanity check: must contain at least one digit and be >= 5 chars
        if len(reg_no) < 5 or not any(c.isdigit() for c in reg_no):
            continue
        # Avoid common false positives like dates (e.g. 2021/2022) or generic words
        if reg_no.isdigit() and len(reg_no) <= 8:
            continue
        if reg_no.upper() in seen:
            continue
        seen.add(reg_no.upper())

        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 25)
        excerpt = text[start:end].strip()
        results.append((reg_no, excerpt))

    return results


def verify_rera(reg_no: str, state: str | None = None, project_name: str | None = None, evidence: list[str] | None = None) -> RERAResult:
    # Auto-detect state from RERA prefix if state is not provided
    clean_reg = reg_no.strip()
    detected_state = state

    if not detected_state or detected_state == "UNKNOWN":
        if re.match(r"^P(?:5\d{9}|\d{11}|R\d{10})$", clean_reg, re.I):
            detected_state = "Maharashtra"
        elif "KA/RERA" in clean_reg.upper():
            detected_state = "Karnataka"
        elif clean_reg.upper().startswith("UPRERAPRJ"):
            detected_state = "Uttar Pradesh"
        elif "HRERA" in clean_reg.upper() or "HARERA" in clean_reg.upper():
            detected_state = "Haryana"

    verifier = get_verifier_for_state(detected_state or "")
    return verifier.verify(clean_reg, project_name=project_name, evidence=evidence)
