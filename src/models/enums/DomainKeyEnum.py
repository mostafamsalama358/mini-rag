from enum import Enum


class DomainKeyEnum(str, Enum):
    """Field pack keys stored on `projects.domain_key`.

    Adding a new domain requires:
      1. Append the value here.
      2. Add an Alembic enum migration (PostgreSQL native ENUM).
      3. Register the pack in `src/fields/registry.yaml`.
      4. Create `src/fields/{key}/` with the required module files.
    """

    GENERIC = "generic"
    PHARMACY = "pharmacy"
    LEGAL = "legal"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def parse(cls, value: str | None) -> "DomainKeyEnum":
        """Return the matching member or fall back to GENERIC.

        Used at read time: an unknown stored value (e.g. a domain removed in
        a later deploy) downgrades safely to `generic` with a logged warning,
        per spec FR-010 / acceptance US4-2.
        """
        if value is None:
            return cls.GENERIC
        for member in cls:
            if member.value == value:
                return member
        return cls.GENERIC
