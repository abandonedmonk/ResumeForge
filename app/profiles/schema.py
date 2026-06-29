"""Dataclasses for the structured candidate profile (YAML-serializable).

Tolerant ``from_dict`` (ignores unknown keys, fills missing) so a hand-edited
profile.yaml or a best-effort PDF extraction never crashes the loader.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields


def _str(value: object) -> str:
    return "" if value is None else str(value).strip()


def _str_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


@dataclass
class Contact:
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> Contact:
        data = data or {}
        return cls(**{f.name: _str(data.get(f.name)) for f in fields(cls)})


@dataclass
class Education:
    institution: str = ""
    city: str = ""
    degree: str = ""
    dates: str = ""
    gpa: str = ""
    coursework: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> Education:
        data = data or {}
        return cls(**{f.name: _str(data.get(f.name)) for f in fields(cls)})


@dataclass
class Experience:
    company: str = ""
    role: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> Experience:
        data = data or {}
        return cls(
            company=_str(data.get("company")),
            role=_str(data.get("role")),
            location=_str(data.get("location")),
            dates=_str(data.get("dates")),
            bullets=_str_list(data.get("bullets")),
        )


@dataclass
class Certification:
    name: str = ""
    issuer: str = ""
    date: str = ""
    url: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> Certification:
        data = data or {}
        return cls(**{f.name: _str(data.get(f.name)) for f in fields(cls)})


@dataclass
class Profile:
    contact: Contact = field(default_factory=Contact)
    education: list[Education] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    certifications: list[Certification] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> Profile:
        data = data or {}
        return cls(
            contact=Contact.from_dict(data.get("contact")),
            education=[Education.from_dict(item) for item in (data.get("education") or [])],
            experience=[Experience.from_dict(item) for item in (data.get("experience") or [])],
            certifications=[Certification.from_dict(item) for item in (data.get("certifications") or [])],
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def is_empty(self) -> bool:
        return not (
            self.contact.name
            or self.education
            or self.experience
            or self.certifications
        )
