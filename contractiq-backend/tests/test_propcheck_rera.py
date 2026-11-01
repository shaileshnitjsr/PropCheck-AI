"""Unit tests for modular RERA verification."""

from rera_verifier import extract_rera_numbers, verify_rera
from rera_verifier.base import RERAStatus
from rera_verifier.maharera import MahaRERAAdapter
from rera_verifier.karnatakarera import KarnatakaRERAAdapter
from rera_verifier.uprera import UPRERAAdapter
from rera_verifier.haryanarera import HaryanaRERAAdapter


def test_maharera_format_validation():
    adapter = MahaRERAAdapter()
    assert adapter.validate_format("P51800000001") is True
    assert adapter.validate_format("P52000012345") is True
    assert adapter.validate_format("INVALID_RERA") is False
    assert adapter.validate_format("12345") is False

    res = adapter.verify("P51800000001", project_name="Sunshine Heights")
    assert res.status == RERAStatus.FORMAT_VALID_OFFLINE_VERIFICATION_PENDING
    assert "maharera.maharashtra.gov.in" in res.official_search_url


def test_karnataka_rera_format_validation():
    adapter = KarnatakaRERAAdapter()
    assert adapter.validate_format("PRM/KA/RERA/1251/310/PR/171015/000412") is True
    assert adapter.validate_format("KA/RERA/1251/310/PR/171015") is True
    assert adapter.validate_format("NOT_A_RERA") is False

    res = adapter.verify("PRM/KA/RERA/1251/310/PR/171015/000412")
    assert res.status == RERAStatus.FORMAT_VALID_OFFLINE_VERIFICATION_PENDING
    assert "rera.karnataka.gov.in" in res.official_portal_url


def test_uprera_format_validation():
    adapter = UPRERAAdapter()
    assert adapter.validate_format("UPRERAPRJ12345") is True
    assert adapter.validate_format("UPRERAPRJ999999") is True
    assert adapter.validate_format("UP_INVALID") is False

    res = adapter.verify("UPRERAPRJ12345")
    assert res.status == RERAStatus.FORMAT_VALID_OFFLINE_VERIFICATION_PENDING
    assert "up-rera.in" in res.official_portal_url


def test_haryanarera_format_validation():
    adapter = HaryanaRERAAdapter()
    assert adapter.validate_format("HRERA-PKL-123-2018") is True
    assert adapter.validate_format("GGM/123/45/2018/12") is True
    assert adapter.validate_format("HR_BAD_FORMAT") is False


def test_extract_rera_numbers_from_text():
    sample_text = """
    This project is registered with MahaRERA under Registration No. P51800000001.
    All plans and approvals are available on the portal.
    For Phase 2, please reference UPRERAPRJ54321.
    """
    found = extract_rera_numbers(sample_text)
    numbers = [num for num, _ in found]
    assert "P51800000001" in numbers
    assert "UPRERAPRJ54321" in numbers


def test_auto_state_inference_for_rera():
    res_mh = verify_rera("P51800000001")
    assert res_mh.state == "Maharashtra"
    assert res_mh.authority == "MahaRERA"

    res_up = verify_rera("UPRERAPRJ65432")
    assert res_up.state == "Uttar Pradesh"
    assert res_up.authority == "UP-RERA"
