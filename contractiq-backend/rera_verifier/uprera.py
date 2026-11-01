"""UP RERA (Uttar Pradesh Real Estate Regulatory Authority) Adapter."""

import re
import urllib.parse
from .base import BaseRERAAdapter


class UPRERAAdapter(BaseRERAAdapter):
    state_name = "Uttar Pradesh"
    authority_name = "UP-RERA"
    portal_url = "https://www.up-rera.in"
    search_url = "https://www.up-rera.in/projects"

    # UP format: UPRERAPRJ followed by digits (e.g. UPRERAPRJ12345 or UPRERAPRJ123456)
    FORMAT_REGEX = re.compile(r"^UPRERAPRJ\d{4,9}$", re.IGNORECASE)

    def validate_format(self, reg_no: str) -> bool:
        clean = reg_no.replace(" ", "").replace("-", "")
        return bool(self.FORMAT_REGEX.match(clean))

    def get_search_url(self, reg_no: str, project_name: str | None = None) -> str:
        clean = reg_no.replace(" ", "").replace("-", "")
        return f"{self.search_url}?reg_no={urllib.parse.quote(clean)}"
