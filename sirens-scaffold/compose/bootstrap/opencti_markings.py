"""Define Sirens marking-definition taxonomy in OpenCTI.

Idempotent: checks for each marking by definition string before creating.
Verifies the standard TLP markings shipped by OpenCTI exist; errors if not.
"""

from __future__ import annotations

import os
import sys

from pycti import OpenCTIApiClient


SIRENS_MARKINGS: list[dict[str, str | int]] = [
    {
        "definition_type": "statement",
        "definition": "SIRENS:INTERNAL",
        "x_opencti_color": "#666666",
        "x_opencti_order": 10,
    },
    {
        "definition_type": "statement",
        "definition": "SIRENS:CUSTOMER_PRIVATE",
        "x_opencti_color": "#cc0000",
        "x_opencti_order": 20,
    },
    {
        "definition_type": "statement",
        "definition": "SIRENS:ATTRIBUTION_DRAFT",
        "x_opencti_color": "#ff8800",
        "x_opencti_order": 30,
    },
    {
        "definition_type": "statement",
        "definition": "SIRENS:ATTRIBUTION_VALIDATED",
        "x_opencti_color": "#00994c",
        "x_opencti_order": 40,
    },
]

REQUIRED_TLP = [
    "TLP:CLEAR",
    "TLP:GREEN",
    "TLP:AMBER",
    "TLP:AMBER+STRICT",
    "TLP:RED",
]


def main() -> int:
    url = os.environ["OPENCTI_URL"]
    token = os.environ["OPENCTI_ADMIN_TOKEN"]
    client = OpenCTIApiClient(url, token, ssl_verify=True, log_level="info")

    existing = client.marking_definition.list(first=500)
    existing_by_def = {m["definition"]: m for m in existing}

    missing_tlp = [t for t in REQUIRED_TLP if t not in existing_by_def]
    if missing_tlp:
        print(f"ERROR: OpenCTI is missing standard TLP markings: {missing_tlp}")
        print("Check OpenCTI bootstrapped cleanly before re-running.")
        return 1

    for m in SIRENS_MARKINGS:
        if m["definition"] in existing_by_def:
            print(f"SKIP  {m['definition']} (exists)")
            continue
        created = client.marking_definition.create(
            definition_type=m["definition_type"],
            definition=m["definition"],
            x_opencti_color=m["x_opencti_color"],
            x_opencti_order=m["x_opencti_order"],
        )
        print(f"CREATE {m['definition']} id={created['id']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
