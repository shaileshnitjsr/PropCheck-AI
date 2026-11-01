"""Generic fallback RERA adapter for other Indian states."""

import re
from .base import BaseRERAAdapter, RERAResult, RERAStatus
import time


class GenericRERAAdapter(BaseRERAAdapter):
    def __init__(self, state_name: str = "National / Other", authority_name: str = "State RERA"):
        self.state_name = state_name
        self.authority_name = authority_name
        self.portal_url = "https://mohua.gov.in/cms/rera.php"
        self.search_url = "https://mohua.gov.in/cms/rera.php"

    def validate_format(self, reg_no: str) -> bool:
        # Generic RERA number validation (at least 6 alphanumeric characters with letters and numbers)
        clean = reg_no.replace(" ", "").replace("-", "").replace("/", "")
        has_letters = bool(re.search(r"[A-Za-z]", clean))
        has_numbers = bool(re.search(r"\d", clean))
        return len(clean) >= 6 and has_letters and has_numbers
