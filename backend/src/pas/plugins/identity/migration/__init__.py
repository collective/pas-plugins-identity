"""Migrations from the packages this one succeeds.

Both migrations are **hard cutovers** with a dry-run report mode. Coexistence
-- running the old plugin and this one side by side -- is explicitly not
supported and not tested: two plugins both claiming to authenticate the
same people is a way to end up with two accounts for one human, which is the
one outcome a stable userid exists to prevent.

Every migration here is:

**Idempotent.** Running it twice does nothing the second time. A migration you
cannot re-run is a migration nobody dares run.

**Reversible only by not committing it.** ``dry_run=True`` reports exactly what
a real run would do and writes nothing at all. Read the report first.

**Loud about what it cannot do.** A migration that silently produces a wrong
identity join is worse than one that refuses: the wrong join surfaces months
later as somebody logging into somebody else's account.
"""

from dataclasses import dataclass
from dataclasses import field


@dataclass
class Report:
    """What a migration did, or would do.

    :ivar dry_run: Whether anything was actually written.
    :ivar identities: ``(provider, subject, userid)`` triples migrated.
    :ivar providers: Provider ids created from the old configuration.
    :ivar skipped: Records deliberately not migrated, with the reason.
    :ivar refusals: Conditions that stopped the migration entirely.
    """

    dry_run: bool = True
    identities: list[tuple[str, str, str]] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        """Whether the migration refused to run.

        :returns: ``True`` when there is at least one refusal.
        """
        return bool(self.refusals)

    def as_dict(self) -> dict:
        """Render the report as plain data, for a view or a log.

        :returns: The report.
        """
        return {
            "dry_run": self.dry_run,
            "refused": self.refused,
            "refusals": list(self.refusals),
            "identities": [list(triple) for triple in self.identities],
            "providers": list(self.providers),
            "skipped": list(self.skipped),
            "counts": {
                "identities": len(self.identities),
                "providers": len(self.providers),
                "skipped": len(self.skipped),
            },
        }


__all__ = ["Report"]
