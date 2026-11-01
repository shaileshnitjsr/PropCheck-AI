"""Unit tests for automatic Indian state detection."""

from state_detector import detect_state_from_texts


def test_clear_maharashtra_detection():
    texts = [
        "AGREEMENT FOR SALE OF APARTMENT",
        "Situated at Flat No. 402, Building A, Pune, Maharashtra 411001",
        "Subject to the provisions of the Maharashtra Stamp Act and MahaRERA.",
    ]
    result = detect_state_from_texts(texts)
    assert result.state == "Maharashtra"
    assert result.confidence >= 0.75
    assert not result.is_conflict
    assert any("pune" in ev.lower() or "maharashtra" in ev.lower() for ev in result.evidence)


def test_clear_karnataka_detection():
    texts = [
        "DEED OF CONVEYANCE - BENGALURU URBAN",
        "The property is located at Whitefield, Bangalore, Karnataka, PIN 560066",
        "Registered under the Karnataka Stamp Act, 1957.",
    ]
    result = detect_state_from_texts(texts)
    assert result.state == "Karnataka"
    assert result.confidence >= 0.75
    assert not result.is_conflict


def test_clear_haryana_detection():
    texts = [
        "BUILDER BUYER AGREEMENT",
        "Sector 54, Golf Course Road, Gurugram, Haryana - 122002",
        "Subject to jurisdiction of courts at Gurugram, HRERA registered.",
    ]
    result = detect_state_from_texts(texts)
    assert result.state == "Haryana"
    assert result.confidence >= 0.70


def test_clear_delhi_detection():
    texts = [
        "LEASE AND LICENSE AGREEMENT - DWARKA, NEW DELHI 110075",
        "Governed by the Delhi Rent Control Act.",
    ]
    result = detect_state_from_texts(texts)
    assert result.state == "Delhi"
    assert result.confidence >= 0.70


def test_unknown_when_no_evidence():
    texts = [
        "CONFIDENTIAL COMMERCIAL AGREEMENT",
        "Clause 1: Definitions and general interpretations.",
        "Clause 2: The parties agree to terms specified in Annexure A.",
    ]
    result = detect_state_from_texts(texts)
    assert result.state == "UNKNOWN"
    assert result.confidence == 0.0
    assert result.evidence == []


def test_conflicting_state_signals():
    # Buyer resides in Delhi, but property and stamp act are in Noida, Uttar Pradesh
    texts = [
        "ALLOTMENT LETTER",
        "Purchaser: Mr. Sharma residing at Dwarka, New Delhi 110075",
        "Property: Flat No. 1204, Sector 78, Noida, Uttar Pradesh 201301",
        "Stamping under Uttar Pradesh Stamp Act.",
    ]
    result = detect_state_from_texts(texts)
    # Uttar Pradesh has more signals (Noida, Uttar Pradesh, 201301, UP Stamp Act)
    assert result.state == "Uttar Pradesh"
    assert result.confidence > 0.5
    # Should identify conflict/multi-state signals in candidate scores
    assert "Delhi" in result.all_candidate_scores
    assert "Uttar Pradesh" in result.all_candidate_scores
