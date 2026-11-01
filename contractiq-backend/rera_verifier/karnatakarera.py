"""Karnataka RERA (K-RERA) Adapter."""

import re
import urllib.parse
from .base import BaseRERAAdapter


class KarnatakaRERAAdapter(BaseRERAAdapter):
    state_name = "Karnataka"
    authority_name = "K-RERA"
    portal_url = "https://rera.karnataka.gov.in"
    search_url = "https://rera.karnataka.gov.in/viewProjectDetails"

    # Karnataka format: PRM/KA/RERA/1251/310/PR/171015/000412 or ACK/KA/RERA/...
    FORMAT_REGEX = re.compile(
        r"^(?:PRM|ACK)/KA/RERA/\d{4}/\d{3}/(?:PR|AG|RA)/\d{6}/\d{6}$|"
        r"^KA/RERA/\d{4}/\d{3}/[A-Z]+/\d+$",
        re.IGNORECASE,
    )

    def validate_format(self, reg_no: str) -> bool:
        clean = reg_no.strip()
        if self.FORMAT_REGEX.match(clean):
            return True
        # Also tolerate clean slashes with slight whitespace
        normalized = re.sub(r"\s*/\s*", "/", clean)
        return bool(self.FORMAT_REGEX.match(normalized)) or ("KA/RERA" in clean.upper() and len(clean) >= 15)

    def get_search_url(self, reg_no: str, project_name: str | None = None) -> str:
        clean = reg_no.strip()
        return f"{self.search_url}?ackNumber={urllib.parse.quote(clean)}"
