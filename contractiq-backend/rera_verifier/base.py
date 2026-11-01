"""Modular RERA Verification Engine for Indian States."""

from enum import Enum
import time
from typing import NamedTuple
from pydantic import BaseModel


class RERAStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FORMAT_VALID_OFFLINE_VERIFICATION_PENDING = "FORMAT_VALID_OFFLINE_VERIFICATION_PENDING"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"
    NOT_FOUND = "NOT_FOUND"
    INVALID_FORMAT = "INVALID_FORMAT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RERAResult(BaseModel):
    registration_number: str
    project_name: str | None = None
    promoter_name: str | None = None
    state: str
    authority: str
    status: RERAStatus
    status_message: str
    verified_at: float
    valid_until: str | None = None
    official_portal_url: str
    official_search_url: str
    evidence: list[str] = []
    disclaimer: str = (
        "RERA registration check reflects official public records and regulatory formats. "
        "Automated connectivity to state portals may be subject to government server availability or CAPTCHAs. "
        "Always independently verify on the official portal link provided."
    )


class BaseRERAAdapter:
    """Base class for state-specific RERA adapters."""
    state_name: str = "Unknown"
    authority_name: str = "RERA"
    portal_url: str = ""
    search_url: str = ""

    def validate_format(self, reg_no: str) -> bool:
        raise NotImplementedError

    def get_search_url(self, reg_no: str, project_name: str | None = None) -> str:
        return self.search_url

    def verify(self, reg_no: str, project_name: str | None = None, evidence: list[str] | None = None) -> RERAResult:
        clean_reg = reg_no.strip()
        is_valid = self.validate_format(clean_reg)
        ev = evidence or []

        if not is_valid:
            return RERAResult(
                registration_number=clean_reg,
                project_name=project_name,
                state=self.state_name,
                authority=self.authority_name,
                status=RERAStatus.INVALID_FORMAT,
                status_message=f"The identifier '{clean_reg}' does not conform to the official {self.authority_name} numbering format.",
                verified_at=time.time(),
                official_portal_url=self.portal_url,
                official_search_url=self.get_search_url(clean_reg, project_name),
                evidence=ev,
            )

        # For state portals: official lookup with timeout & safe fallback.
        # Government RERA portals typically enforce CAPTCHA or Cloudflare/NIC firewalls.
        # We perform an honest format verification and provide direct pre-filled / portal query links.
        return RERAResult(
            registration_number=clean_reg,
            project_name=project_name,
            state=self.state_name,
            authority=self.authority_name,
            status=RERAStatus.FORMAT_VALID_OFFLINE_VERIFICATION_PENDING,
            status_message=(
                f"Valid {self.authority_name} registration number format detected. "
                f"Government state portal requires manual verification via official public search."
            ),
            verified_at=time.time(),
            official_portal_url=self.portal_url,
            official_search_url=self.get_search_url(clean_reg, project_name),
            evidence=ev,
        )
