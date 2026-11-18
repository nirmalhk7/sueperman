"""Guidance for reviewed document labels; never proof or handling instructions."""

import hashlib
from pathlib import Path

_SOURCES = {
    "26-792": "https://www.cpsc.gov/Recalls/2026/NEWDERY-Power-Banks-Recalled-Due-to-Fire-and-Burn-Hazards-Risk-of-Serious-Injury-Sold-on-Amazon",
    "26-610": "https://www.cpsc.gov/Recalls/2026/Flaunt-Recalls-Magsafe-Battery-Chargers-Due-to-Risk-of-Serious-Injury-or-Death-from-Fire-and-Burn-Hazards",
    "25-390": "https://www.cpsc.gov/Recalls/2025/iStore-Magnetic-Wireless-Power-Banks-Recalled-Due-to-Fire-and-Burn-Hazards-Imported-by-Tomauri",
    "25-248": "https://www.cpsc.gov/Recalls/2025/Baseus-Portable-Chargers-Recalled-Due-to-Fire-Hazard-Sold-on-Amazon-com-by-Shenzhen-Baseus-Technology",
}
_PHOTO = (
    "Read the current official safety instructions before preparing any photo.",
    "Check the model or serial number requested by this item; do not guess an unreadable identifier.",
    "Follow the notice's exact photo and marking requirements. Keep the requested photo locally; this checklist does not upload it.",
)
_DECLARATION = (
    "Review the official notice for the required confirmation and safety instructions.",
    "Marking preparation ready does not attest disposal or make a declaration. Any declaration must come from you through the official process.",
)
_CONDITIONAL = (
    "Whether this photo is required depends on your order number. Check the official notice; a missing order number in this app does not establish that you have none.",
    "If the requirement applies, follow the notice's exact photo instructions and keep the evidence locally.",
)
_GUIDES: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    "26-792": {
        "Photo of power bank with model and serial number and official required markings": ("required", _PHOTO),
        "User confirmation of lawful disposal (never prefilled)": ("required", _DECLARATION),
    },
    "26-610": {
        "Front photo with Recalled, your initials and registration date, as directed by the official notice": ("required", _PHOTO),
        "Back photo showing model E33A": ("required", _PHOTO),
    },
    "25-390": {
        "Front photo with Recalled and date, as directed by the official notice": ("required", _PHOTO),
        "Back photo showing the model number": ("required", _PHOTO),
    },
    "25-248": {
        "Photo showing model number and serial number": ("required", _PHOTO),
        "If no order number, photo showing name and date written on the charger as directed by the notice": ("unknown", _CONDITIONAL),
        "User confirmation of lawful disposal (never prefilled)": ("required", _DECLARATION),
    },
}


def policy_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def plan(recall, labels):
    reviewed = _SOURCES.get(recall.reference) == recall.official_url
    catalog = _GUIDES.get(recall.reference, {}) if reviewed else {}
    items = []
    for label in labels:
        requirement, steps = catalog.get(label, ("unknown", (
            "We have not reviewed preparation instructions for this item. Confirm what is needed in the current official notice; do not infer a requirement from this checklist.",
        )))
        items.append({"requirement": requirement, "preparation_steps": list(steps)})
    return {"items": items, "mode": "guidance_only", "source_url": recall.official_url,
        "source_mode": recall.mode, "observed_at": recall.fetched_at.isoformat(),
        "optional_tips": [{"requirement": "optional", "origin": "organizer_tip",
                           "label": "Keep the official notice link with your local purchase records."}],
        "limitation": "No evidence files are collected or verified by this checklist. Readiness is self-reported; no declaration or external submission is made."}
