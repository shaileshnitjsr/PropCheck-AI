"""MahaRERA (Maharashtra Real Estate Regulatory Authority) Adapter."""

import re
import urllib.parse
from .base import BaseRERAAdapter, RERAResult, RERAStatus
import time


class MahaRERAAdapter(BaseRERAAdapter):
    state_name = "Maharashtra"
    authority_name = "MahaRERA"
    portal_url = "https://maharera.maharashtra.gov.in"
    search_url = "https://maharera.maharashtra.gov.in/projects-searchResult"

    # MahaRERA format: P5 followed by 9-10 digits (or legacy P followed by 11 digits, or PR followed by 10 digits)
    FORMAT_REGEX = re.compile(r"^P(?:5\d{9,10}|\d{11}|R\d{10})$", re.IGNORECASE)

    def validate_format(self, reg_no: str) -> bool:
        clean = reg_no.replace(" ", "").replace("-", "")
        return bool(self.FORMAT_REGEX.match(clean))

    def get_search_url(self, reg_no: str, project_name: str | None = None) -> str:
        clean = reg_no.replace(" ", "").replace("-", "")
        # MahaRERA search query parameter
        return f"{self.search_url}?project_name=&cert_no={urllib.parse.quote(clean)}"
