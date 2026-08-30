"""Migrations from the packages this one succeeds.

Both migrations are **hard cutovers** with a dry-run report mode. Coexistence
-- running the old plugin and this one side by side -- is explicitly not
supported and not tested: two plugins both claiming to authenticate the
same people is a way to end up with two accounts for one human, which is the
one outcome a stable userid exists to prevent.

Every migration here is:

**Through the plugin, never straight into the store.** ``store.add`` writes the
identity join and nothing else; ``plugin.link`` writes it and fires
``IdentityLinked``, which is what mints the Profile that *is* the user on a
site where principals are content.

The distinction is easy to lose, because both migrations read as correct with
either one: the identity resolves, and the person turns up at their first
login. What they do not do, with ``store.add``, is exist before it -- so they
cannot be found in ``@users``, granted a role or added to a group, and they
vanish entirely when the old plugin is removed, which is what the hard cutover
below tells an operator to do. Both migrations were written that way and both
were changed together.

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
    :ivar users: Userids that have a Profile once the migration has run. On a
        dry run, those that would gain one.
    :ivar skipped: Records deliberately not migrated, with the reason.
    :ivar refusals: Conditions that stopped the migration entirely.
    """

    dry_run: bool = True
    identities: list[tuple[str, str, str]] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    users: list[str] = field(default_factory=list)
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
            "users": list(self.users),
            "skipped": list(self.skipped),
            "counts": {
                "identities": len(self.identities),
                "providers": len(self.providers),
                "users": len(self.users),
                "skipped": len(self.skipped),
            },
        }


def profiles_for(userids) -> list[str]:
    """Return those userids that have a Profile.

    Used to report what a migration produced, and -- on a dry run, where it is
    called before anything is written -- what it would produce.

    :param userids: The userids to look at.
    :returns: Those with a Profile, sorted.
    """
    from pas.plugins.identity.core.subscribers import get_profile

    return sorted(uid for uid in set(userids) if get_profile(uid) is not None)


__all__ = ["Report", "profiles_for"]
