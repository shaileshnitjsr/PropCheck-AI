"""Haryana RERA (HRERA) Adapter."""

import re
import urllib.parse
from .base import BaseRERAAdapter


class HaryanaRERAAdapter(BaseRERAAdapter):
    state_name = "Haryana"
    authority_name = "HRERA"
    portal_url = "https://haryanarera.gov.in"
    search_url = "https://haryanarera.gov.in/project/project_summary"

    # HRERA formats: HRERA-PKL-123-2018 or GGM/123/45/2018/12 or RC/REP/HARERA/GGM/...
    FORMAT_REGEX = re.compile(
        r"^(?:HRERA-(?:PKL|GGM)-\d+(?:-\d+)?|GGM/\d+/\d+/\d+/\d+|RC/REP/HARERA/(?:GGM|PKL)/.*|\d+\s+OF\s+\d{4})$",
        re.IGNORECASE,
    )

    def validate_format(self, reg_no: str) -> bool:
        clean = reg_no.strip()
        return bool(self.FORMAT_REGEX.match(clean)) or ("HARERA" in clean.upper() or "HRERA" in clean.upper())

    def get_search_url(self, reg_no: str, project_name: str | None = None) -> str:
        clean = reg_no.strip()
        return f"{self.search_url}?project_id={urllib.parse.quote(clean)}"
