# bursary/utils/mock_verification.py
"""
Mock verification helpers for local development.
Replace these with real NRB / eCitizen / NEMIS integration when ready.
"""

from typing import Optional, Tuple

# Simple, configurable prefix rules for testing.
MOCK_RULES = {
    "samburu": {
        "id_prefix": "2",        # IDs starting with "2" → Samburu
        "nemis_prefix": "SA",    # NEMIS starting with "SA"
        "constituency": "Samburu West",
    },
    "nairobi": {
        "id_prefix": "1",        # IDs starting with "1" → Nairobi
        "nemis_prefix": "NA",
        "constituency": "Westlands",
    },
}


def verify_id(
    id_number: str,
    county_name: Optional[str] = None,
    constituency_name: Optional[str] = None,
) -> Tuple[bool, str, str, str]:
    """
    Mock verify a national ID belongs to the active site's county/constituency.
    Returns (is_valid, message, verified_county, verified_constituency).
    """
    if not id_number:
        return False, "ID number is required.", None, None

    # Use county if available, otherwise constituency
    context_name = county_name or constituency_name
    if not context_name:
        return False, "Site profile county/constituency not configured.", None, None

    key = context_name.strip().lower()
    rules = MOCK_RULES.get(key)

    if rules:
        prefix = rules.get("id_prefix", "")
        if id_number.startswith(prefix):
            return True, "ID verified successfully.", county_name or "DefaultCounty", constituency_name or rules.get("constituency")
        return False, f"ID {id_number} does not match {context_name}.", None, None

    # Default fallback: accept if numeric and length >= 6
    if id_number.isdigit() and len(id_number) >= 6:
        return True, "ID verified under default rules.", county_name or "DefaultCounty", constituency_name or "DefaultConstituency"

    return False, "Invalid ID format.", None, None


def verify_nemis(
    nemis_number: str,
    county_name: Optional[str] = None,
    constituency_name: Optional[str] = None,
    guardian_id: Optional[str] = None,
) -> Tuple[bool, str, str, str]:
    """
    Mock verify a NEMIS + guardian composite.
    Returns (is_valid, message, verified_county, verified_constituency).
    """
    if not nemis_number:
        return False, "NEMIS number is required.", None, None

    # Use county if available, otherwise constituency
    context_name = county_name or constituency_name
    if not context_name:
        return False, "Site profile county/constituency not configured.", None, None

    key = context_name.strip().lower()
    rules = MOCK_RULES.get(key)

    if rules:
        n_prefix = rules.get("nemis_prefix", "")
        g_prefix = rules.get("id_prefix", "")
        if nemis_number.upper().startswith(n_prefix):
            if guardian_id and guardian_id.startswith(g_prefix):
                return True, "NEMIS verified successfully.", county_name or "DefaultCounty", constituency_name or rules.get("constituency")
            return True, "NEMIS verified (guardian check skipped).", county_name or "DefaultCounty", constituency_name or rules.get("constituency")
        return False, f"NEMIS {nemis_number} does not match {context_name}.", None, None

    # Fallback: accept if nemis length >= 4
    if len(nemis_number) >= 4:
        return True, "NEMIS verified under default rules.", county_name or "DefaultCounty", constituency_name or "DefaultConstituency"

    return False, "Invalid NEMIS format.", None, None




