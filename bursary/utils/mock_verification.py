import time
import random
from typing import Tuple, Optional

"""
This module simulates a Government National ID verification API.
It now validates ID number, first name, and last name against the
national registry, ensuring identity and regional integrity.
"""

# ---------------------------
# Simulated National Database
# ---------------------------

MOCK_DATABASE = [
    {"id_number": "23456789", "name": "John Lekupe", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456790", "name": "Lemayan Lenkei", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456791", "name": "Naisula Leshao", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456792", "name": "Lekishon Lolosoli", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456793", "name": "Mporoko Lkeri", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456794", "name": "Nasieku Lolban", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456795", "name": "Leshao Lesorogol", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456796", "name": "Nkeno Letepes", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456797", "name": "Lenguris Lkinya", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456798", "name": "Nasiru Lepapa", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456799", "name": "Lesur Lekishon", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456800", "name": "Lekan Lderit", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456801", "name": "Naeku Lengai", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456802", "name": "Lenkai Lemerig", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456803", "name": "Lemorijo Lenkume", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456804", "name": "Nasaria Lparash", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456805", "name": "Lemayian Lkoteyia", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456806", "name": "Naselina Lkeno", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456807", "name": "Lkunyori Leketan", "county": "Samburu", "constituency": "Samburu West"},
    {"id_number": "23456808", "name": "Lemian Lesipeti", "county": "Samburu", "constituency": "Samburu West"},
    # Out-of-region examples
    {"id_number": "14567890", "name": "Mary Wanjiku", "county": "Nairobi", "constituency": "Westlands"},
    {"id_number": "27890123", "name": "James Kariuki", "county": "Kiambu", "constituency": "Thika Town"},
    # Samburu North
    {"id_number": "23456001", "name": "Lerionka Lolchoki", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456002", "name": "Naisula Lemiso", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456003", "name": "Lemayan Lkutuk", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456004", "name": "Ntaile Lesorogol", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456005", "name": "Leramparai Leleto", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456006", "name": "Naperu Letai", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456007", "name": "Lemayan Leruk", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456008", "name": "Lemiso Lekuta", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456009", "name": "Lesimiti Leshun", "county": "Samburu", "constituency": "Samburu North"},
    {"id_number": "23456010", "name": "Lkanto Lolkile", "county": "Samburu", "constituency": "Samburu North"},
    # Samburu East
    {"id_number": "23457001", "name": "Lemayian Lelerai", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457002", "name": "Naimutie Lenkai", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457003", "name": "Lesiankei Lerumo", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457004", "name": "Lemiruni Lpetai", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457005", "name": "Lerima Lesiak", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457006", "name": "Naisula Letoiye", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457007", "name": "Lesampu Lesoroi", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457008", "name": "Lepore Lesim", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457009", "name": "Leserian Leken", "county": "Samburu", "constituency": "Samburu East"},
    {"id_number": "23457010", "name": "Leruk Lendoiya", "county": "Samburu", "constituency": "Samburu East"},
]


def simulate_network_latency():
    """Adds slight delay to mimic a real API request."""
    time.sleep(random.uniform(0.4, 1.2))

def verify_id(
    id_number: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    county_name: Optional[str] = None,
    constituency_name: Optional[str] = None,
) -> Tuple[bool, str, Optional[str], Optional[str], Optional[str]]:
    """
    Verifies ID number + name + region combination.
    Returns (is_valid, message, county, constituency, full_name)
    """
    simulate_network_latency()

    # Ensure at least one regional context is provided
    if not county_name and not constituency_name:
        return (
            False,
            "Regional context missing. This site must be linked to a county or constituency to verify applicants.",
            None,
            None,
            None,
        )

    if not id_number:
        return False, "ID number is required.", None, None, None

    record = next((r for r in MOCK_DATABASE if r["id_number"] == id_number), None)
    if not record:
        return False, "ID not found in the national database.", None, None, None

    # --- Name matching ---
    record_names = record["name"].strip().lower().split(maxsplit=1)
    record_first, record_last = record_names if len(record_names) == 2 else (record_names[0], "")

    if first_name and record_first != first_name.strip().lower():
        return False, f"First name does not match records for ID {id_number}.", None, None, None

    if last_name and record_last != last_name.strip().lower():
        return False, f"Last name does not match records for ID {id_number}.", None, None, None

    # --- Region validation ---
    record_county = record["county"]
    record_constituency = record["constituency"]

    # Constituency-based site: must match constituency
    if constituency_name:
        if record_constituency.lower() != constituency_name.lower():
            return (
                False,
                f"The ID entered is not registered within this region.",
                record_county,
                record_constituency,
                record["name"],
            )

    # County-based site: must match county
    elif county_name:
        if record_county.lower() != county_name.lower():
            return (
                False,
                f"The ID entered is not registered within this region.",
                record_county,
                record_constituency,
                record["name"],
            )

    # Success: return the record name as the fifth value
    return True, "✅ ID verified successfully.", record_county, record_constituency, record["name"]










