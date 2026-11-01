"""Automatic Indian state detection from property documents and legal instruments."""

import re
from typing import NamedTuple

class StateEvidence(NamedTuple):
    state: str
    signal_type: str  # 'act', 'city_district', 'pincode', 'explicit_state'
    matched_text: str
    weight: float

# Normalized Indian States & UTs mapping
INDIAN_STATES = {
    "Maharashtra": {
        "aliases": ["maharashtra", "maha", "mh", "bombay state"],
        "cities": ["mumbai", "bombay", "pune", "thane", "navi mumbai", "nagpur", "nashik", "aurangabad", "chhatrapati sambhajinagar", "solapur", "kolhapur", "vasai", "virar", "kalyan", "dombivli", "panvel", "raigad", "pimpri", "chinchwad"],
        "acts": ["maharashtra stamp act", "bombay stamp act", "maharashtra rent control act", "maharashtra ownership flats act", "mofa"],
        "pin_prefixes": ["40", "41", "42", "43", "44"],
        "rera_prefix": "maharera",
    },
    "Karnataka": {
        "aliases": ["karnataka", "ka", "mysore state"],
        "cities": ["bengaluru", "bangalore", "mysuru", "mysore", "mangaluru", "mangalore", "hubballi", "hubli", "dharwad", "belagavi", "belgaum", "kalaburagi", "gulbarga", "davangere", "bellary", "ballari", "udupi", "tumakuru", "tumkur", "devenahalli", "whitefield", "electronic city", "sarjapur", "yelahanka"],
        "acts": ["karnataka stamp act", "karnataka rent act", "karnataka ownership flats act"],
        "pin_prefixes": ["56", "57", "58", "59"],
        "rera_prefix": "k-rera",
    },
    "Delhi": {
        "aliases": ["delhi", "nct of delhi", "national capital territory of delhi", "dl", "new delhi"],
        "cities": ["new delhi", "delhi", "dwarka", "rohini", "saket", "vasant kunj", "connaught place", "hauz khas", "janakpuri", "lajpat nagar", "karol bagh"],
        "acts": ["delhi rent control act", "indian stamp (delhi amendment) act"],
        "pin_prefixes": ["11"],
        "rera_prefix": "dlrera",
    },
    "Uttar Pradesh": {
        "aliases": ["uttar pradesh", "up", "u.p."],
        "cities": ["noida", "greater noida", "ghaziabad", "lucknow", "kanpur", "agra", "varanasi", "prayagraj", "allahabad", "meerut", "bareilly", "aligarh", "moradabad", "gorakhpur", "noida extension", "greater noida west", "yamuna expressway"],
        "acts": ["uttar pradesh stamp act", "up urban buildings act"],
        "pin_prefixes": ["20", "21", "22", "23", "24", "25", "26", "27", "28"],
        "rera_prefix": "uprera",
    },
    "Haryana": {
        "aliases": ["haryana", "hr", "h.r."],
        "cities": ["gurugram", "gurgaon", "faridabad", "panchkula", "sonipat", "sonepat", "panipat", "karnal", "rohtak", "hisar", "ambala", "sohna", "manesar", "bahadurgarh"],
        "acts": ["haryana stamp act", "haryana urban rent control act"],
        "pin_prefixes": ["12", "13"],
        "rera_prefix": "hrera",
    },
    "Telangana": {
        "aliases": ["telangana", "ts", "tg", "t.s."],
        "cities": ["hyderabad", "secunderabad", "cyberabad", "warangal", "nizamabad", "karimnagar", "khammam", "gachibowli", "hitec city", "kondapur", "madhapur", "jubilee hills", "banjara hills", "kokapet", "tellapur"],
        "acts": ["telangana stamp act", "telangana buildings control act"],
        "pin_prefixes": ["50"],
        "rera_prefix": "tsrera",
    },
    "Tamil Nadu": {
        "aliases": ["tamil nadu", "tamilnadu", "tn", "t.n.", "madras state"],
        "cities": ["chennai", "madras", "coimbatore", "madurai", "tiruchirappalli", "trichy", "salem", "tiruppur", "omr", "ecr", "velachery", "tambaram"],
        "acts": ["tamil nadu stamp act", "tamil nadu buildings lease and rent control act"],
        "pin_prefixes": ["60", "61", "62", "63", "64"],
        "rera_prefix": "tnrera",
    },
    "Gujarat": {
        "aliases": ["gujarat", "gj", "g.j."],
        "cities": ["ahmedabad", "surat", "vadodara", "baroda", "rajkot", "bhavnagar", "jamnagar", "gandhinagar", "gift city"],
        "acts": ["gujarat stamp act", "bombay rent control act as applicable to gujarat"],
        "pin_prefixes": ["36", "37", "38", "39"],
        "rera_prefix": "gujrera",
    },
    "Rajasthan": {
        "aliases": ["rajasthan", "rj", "r.j."],
        "cities": ["jaipur", "jodhpur", "kota", "bikaner", "ajmer", "udaipur", "bhiwadi", "alwar"],
        "acts": ["rajasthan stamp act", "rajasthan rent control act"],
        "pin_prefixes": ["30", "31", "32", "33", "34"],
        "rera_prefix": "rajrera",
    },
    "West Bengal": {
        "aliases": ["west bengal", "wb", "w.b."],
        "cities": ["kolkata", "calcutta", "howrah", "new town", "rajarhat", "salt lake", "durgapur", "asansol", "siliguri"],
        "acts": ["bengal stamp act", "west bengal premises tenancy act"],
        "pin_prefixes": ["70", "71", "72", "73", "74"],
        "rera_prefix": "wbhira",
    },
    "Kerala": {
        "aliases": ["kerala", "kl", "k.l."],
        "cities": ["kochi", "cochin", "thiruvananthapuram", "trivandrum", "kozhikode", "calicut", "thrissur", "kollam", "palakkad"],
        "acts": ["kerala stamp act", "kerala buildings lease and rent control act"],
        "pin_prefixes": ["67", "68", "69"],
        "rera_prefix": "k-rera-kerala",
    },
    "Andhra Pradesh": {
        "aliases": ["andhra pradesh", "ap", "a.p."],
        "cities": ["visakhapatnam", "vizag", "vijayawada", "guntur", "nellore", "tirupati", "kakinada", "amaravati"],
        "acts": ["andhra pradesh stamp act"],
        "pin_prefixes": ["51", "52", "53"],
        "rera_prefix": "aprera",
    },
    "Madhya Pradesh": {
        "aliases": ["madhya pradesh", "mp", "m.p."],
        "cities": ["bhopal", "indore", "gwalior", "jabalpur", "ujjain"],
        "acts": ["madhya pradesh stamp act"],
        "pin_prefixes": ["45", "46", "47", "48"],
        "rera_prefix": "mprera",
    },
    "Punjab": {
        "aliases": ["punjab", "pb", "p.b."],
        "cities": ["chandigarh", "mohali", "ludhiana", "amritsar", "jalandhar", "patiala", "new chandigarh"],
        "acts": ["punjab stamp act"],
        "pin_prefixes": ["14", "15", "16"],
        "rera_prefix": "punjabrera",
    },
    "Goa": {
        "aliases": ["goa", "ga"],
        "cities": ["panaji", "panjim", "margao", "vasco da gama", "mapusa", "porvorim", "calangute", "candolim"],
        "acts": ["goa stamp act", "goa buildings lease act"],
        "pin_prefixes": ["403"],
        "rera_prefix": "goarera",
    },
}

PIN_PATTERN = re.compile(r"\b([1-9]\d{5})\b")


def extract_signals(text: str) -> list[StateEvidence]:
    """Scan text for Indian state signals and return evidence list."""
    lowered = text.casefold()
    signals: list[StateEvidence] = []

    for state, info in INDIAN_STATES.items():
        # Check stamp/tenancy acts (very strong signal: weight 4.0)
        for act in info["acts"]:
            if act in lowered:
                idx = lowered.find(act)
                snippet = text[max(0, idx - 15):min(len(text), idx + len(act) + 20)].strip()
                signals.append(StateEvidence(state, "act", snippet, 4.0))

        # Check explicit state mention (weight 2.5)
        for alias in info["aliases"]:
            # word boundary check
            pattern = rf"\b{re.escape(alias)}\b"
            match = re.search(pattern, lowered)
            if match:
                start = match.start()
                snippet = text[max(0, start - 15):min(len(text), start + len(alias) + 20)].strip()
                signals.append(StateEvidence(state, "explicit_state", snippet, 2.5))
                break  # don't duplicate multiple aliases for same state in one chunk

        # Check cities / districts (weight 2.0)
        for city in info["cities"]:
            pattern = rf"\b{re.escape(city)}\b"
            match = re.search(pattern, lowered)
            if match:
                start = match.start()
                snippet = text[max(0, start - 15):min(len(text), start + len(city) + 20)].strip()
                signals.append(StateEvidence(state, "city_district", snippet, 2.0))
                break  # take at most one primary city per state per chunk

    # Check PIN codes (weight 1.5)
    for pin_match in PIN_PATTERN.finditer(text):
        pin = pin_match.group(1)
        for state, info in INDIAN_STATES.items():
            if any(pin.startswith(prefix) for prefix in info["pin_prefixes"]):
                idx = pin_match.start()
                snippet = text[max(0, idx - 15):min(len(text), idx + 25)].strip()
                signals.append(StateEvidence(state, "pincode", snippet, 1.5))
                break

    return signals


class DetectionResult:
    def __init__(
        self,
        state: str,
        confidence: float,
        evidence: list[str],
        signals: list[dict[str, str]],
        is_conflict: bool = False,
        all_candidate_scores: dict[str, float] | None = None,
    ):
        self.state = state
        self.confidence = round(confidence, 2)
        self.evidence = evidence
        self.signals = signals
        self.is_conflict = is_conflict
        self.all_candidate_scores = all_candidate_scores or {}

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "signals": self.signals,
            "is_conflict": self.is_conflict,
            "all_candidate_scores": self.all_candidate_scores,
        }


def detect_state_from_texts(texts: list[str]) -> DetectionResult:
    """Analyze a collection of text chunks from property documents to detect the Indian state."""
    scores: dict[str, float] = {}
    evidence_by_state: dict[str, list[StateEvidence]] = {}

    for idx, text in enumerate(texts):
        # Give higher weight to opening texts (usually title, jurisdiction, property schedule)
        multiplier = 1.5 if idx < 3 else 1.0
        chunk_signals = extract_signals(text)
        for sig in chunk_signals:
            scores[sig.state] = scores.get(sig.state, 0.0) + (sig.weight * multiplier)
            evidence_by_state.setdefault(sig.state, []).append(sig)

    if not scores:
        return DetectionResult(
            state="UNKNOWN",
            confidence=0.0,
            evidence=[],
            signals=[],
            is_conflict=False,
            all_candidate_scores={},
        )

    # Sort candidates by score
    sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_state, top_score = sorted_candidates[0]
    
    # Check for conflict
    is_conflict = False
    if len(sorted_candidates) > 1:
        runner_up_state, runner_up_score = sorted_candidates[1]
        # If runner up is close (within 75% of top score) and has significant weight
        if runner_up_score >= 3.0 and (runner_up_score / top_score) > 0.75:
            is_conflict = True

    # Calculate calibrated confidence:
    # 2.0 (single city mention) ~ 0.50
    # 4.0 (act or state+city) ~ 0.75
    # 8.0+ (multiple concurring signals) ~ 0.95
    confidence = min(0.99, max(0.2, top_score / (top_score + 2.5)))
    if is_conflict:
        confidence = max(0.3, confidence * 0.65)

    ev_list = [f"[{e.signal_type.upper()}] {e.matched_text}" for e in evidence_by_state.get(top_state, [])[:6]]
    sig_dicts = [
        {"state": e.state, "type": e.signal_type, "text": e.matched_text, "weight": str(e.weight)}
        for e in evidence_by_state.get(top_state, [])[:8]
    ]

    return DetectionResult(
        state=top_state,
        confidence=confidence,
        evidence=ev_list,
        signals=sig_dicts,
        is_conflict=is_conflict,
        all_candidate_scores={k: round(v, 2) for k, v in sorted_candidates},
    )
