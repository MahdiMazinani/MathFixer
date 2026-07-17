from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThesisProfile:
    key: str
    title_fa: str
    title_en: str
    description: str


# Profiles are diagnostic labels, not claims of official university endorsement.
THESIS_PROFILES = (
    ThesisProfile("generic", "عمومی", "Generic thesis", "Persian thesis diagnostics without changing institutional formatting."),
    ThesisProfile("sharif", "دانشگاه صنعتی شریف", "Sharif", "Compatibility checks for a user-supplied Sharif template."),
    ThesisProfile("tehran", "دانشگاه تهران", "University of Tehran", "Compatibility checks for a user-supplied Tehran template."),
    ThesisProfile("amirkabir", "دانشگاه صنعتی امیرکبیر", "Amirkabir", "Compatibility checks for a user-supplied Amirkabir template."),
    ThesisProfile("tabriz", "دانشگاه تبریز", "University of Tabriz", "Compatibility checks for a user-supplied Tabriz template."),
    ThesisProfile("azad", "دانشگاه آزاد", "Islamic Azad University", "Compatibility checks for a user-supplied Azad template."),
)
