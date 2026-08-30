"""The document format, and what refuses one that is not it.

A document is a single JSON object:

.. code-block:: json

   {
     "version": 1,
     "generator": "pas.plugins.identity",
     "created": "2026-08-30T18:04:11+00:00",
     "site": "plone",
     "groups": [
       {
         "group_id": "site-editors",
         "title": "Site Editors",
         "description": "",
         "group_ids": ["staff"]
       }
     ],
     "users": [
       {
         "userid": "8f2c1e5b9a7d4c6e8f0a1b2c3d4e5f60",
         "login": "ericof",
         "fullname": "Érico Andrei",
         "emails": ["erico@plone.org"],
         "home_page": "",
         "description": "",
         "location": "",
         "group_ids": ["site-editors"],
         "identities": [
           {
             "provider": "github",
             "subject": "1234567",
             "created": "2026-01-04T09:12:00+00:00",
             "last_login": "2026-08-30T07:55:03+00:00",
             "groups": ["site-editors"],
             "claims": {"fullname": "Érico Andrei", "email": "erico@plone.org"}
           }
         ]
       }
     ]
   }

**``userid`` is the whole point.** It travels verbatim, because the target
site's local roles, ownerships and sharing entries are all written against it.
An import that minted new ids would produce a site full of content owned by
nobody, and would do it silently.

**No credentials, ever.** There is no password field and no
``client_secret``, in either direction. A password hash is
:mod:`~pas.plugins.identity.core.behaviors.password`'s business and it stays
in the site that holds it; an exported document is a file that gets copied
around, and the one thing it must never be is a way in.

**No audit entries.** They are a per-user login history including, on a site
that opted in, an IP address -- the most sensitive thing this package stores
and the least useful thing to move. ``GET @audit-log`` reads them where they
are, under a permission.

**Order matters on the way in, not on the way out.** Groups are written before
users because a user's ``group_ids`` names them, and a group's own
``group_ids`` -- a group inside a group -- is applied after every group
exists, because nesting can name a group that comes later in the list.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any


#: Bumped when a change to the format would make an older reader wrong. A
#: document from the future is refused rather than read optimistically: the
#: failure mode of guessing here is a half-imported set of accounts.
DOCUMENT_VERSION = 1

#: What :func:`~pas.plugins.identity.exportimport.exporter.export_site` writes
#: into ``generator``, so a document found on disk in two years says what made
#: it.
GENERATOR = "pas.plugins.identity"

#: Profile fields carried for each user. ``userid`` and ``login`` are handled
#: separately: they are required, and they are the two that must not be
#: treated as optional text.
USER_FIELDS = (
    "fullname",
    "home_page",
    "description",
    "location",
)

#: Group fields carried for each group, beside the required ``group_id``.
GROUP_FIELDS = (
    "title",
    "description",
)


class ExportImportError(Exception):
    """A document could not be read, or a site could not be written."""


@dataclass
class Result:
    """What an export or an import did, or would do.

    Deliberately the same shape as
    :class:`pas.plugins.identity.migration.Report`, because an operator
    reading one has just read the other.

    :ivar dry_run: Whether anything was actually written.
    :ivar users: Userids created or updated.
    :ivar groups: Group ids created or updated.
    :ivar identities: ``(provider, subject, userid)`` triples written.
    :ivar skipped: Records deliberately not written, each with its reason.
    :ivar refusals: Conditions that stopped the run entirely.
    """

    dry_run: bool = False
    users: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    identities: list[tuple[str, str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        """Whether the run refused to do anything.

        :returns: ``True`` when there is at least one refusal.
        """
        return bool(self.refusals)

    def as_dict(self) -> dict[str, Any]:
        """Render the result as plain data, for a log or a service.

        :returns: The result.
        """
        return {
            "dry_run": self.dry_run,
            "refused": self.refused,
            "refusals": list(self.refusals),
            "users": list(self.users),
            "groups": list(self.groups),
            "identities": [list(triple) for triple in self.identities],
            "skipped": list(self.skipped),
            "counts": {
                "users": len(self.users),
                "groups": len(self.groups),
                "identities": len(self.identities),
                "skipped": len(self.skipped),
            },
        }

    def summary(self) -> list[str]:
        """Render the result as lines a CLI can print.

        :returns: One line per fact worth reporting.
        """
        if self.refused:
            return [f"refused: {reason}" for reason in self.refusals]
        lines = [
            f"{len(self.users)} users",
            f"{len(self.groups)} groups",
            f"{len(self.identities)} identities",
        ]
        if self.dry_run:
            lines.insert(0, "dry run -- nothing was written")
        lines.extend(f"skipped: {reason}" for reason in self.skipped)
        return lines


def _require(condition: bool, message: str) -> None:
    """Refuse unless a condition holds.

    :param condition: What must be true.
    :param message: What to say when it is not.
    :raises ExportImportError: When the condition is false.
    """
    if not condition:
        raise ExportImportError(message)


def validate(document: Any) -> dict[str, Any]:
    """Check a document and return it, or refuse.

    Structural only: it says the document is shaped like a document, not that
    the site can accept it. Whether a userid collides, whether a group exists,
    whether an identity is already linked to somebody else -- those are
    questions about a site and the importer asks them there, one record at a
    time, so that a single bad row is a skip rather than a refusal.

    :param document: The parsed JSON.
    :returns: The same document, once it is known to be one.
    :raises ExportImportError: When it is not.
    """
    _require(isinstance(document, dict), "The document is not a JSON object")

    version = document.get("version")
    _require(
        isinstance(version, int),
        f"The document has no integer version, but {version!r}",
    )
    _require(
        version <= DOCUMENT_VERSION,
        f"The document is version {version}; this package reads up to "
        f"{DOCUMENT_VERSION}. Guessing at a newer format would half-import "
        f"a set of accounts, so it refuses instead.",
    )

    users = document.get("users", [])
    groups = document.get("groups", [])
    _require(isinstance(users, list), "'users' is not a list")
    _require(isinstance(groups, list), "'groups' is not a list")

    for index, user in enumerate(users):
        _require(isinstance(user, dict), f"users[{index}] is not an object")
        _require(
            bool(user.get("userid")),
            f"users[{index}] has no userid, and a userid cannot be invented: "
            f"every local role and ownership in the target site is written "
            f"against it",
        )
        identities = user.get("identities", [])
        _require(
            isinstance(identities, list),
            f"users[{index}]['identities'] is not a list",
        )
        for position, identity in enumerate(identities):
            _require(
                isinstance(identity, dict),
                f"users[{index}]['identities'][{position}] is not an object",
            )
            _require(
                bool(identity.get("provider")) and bool(identity.get("subject")),
                f"users[{index}]['identities'][{position}] needs both a "
                f"provider and a subject; either alone identifies nobody",
            )

    for index, group in enumerate(groups):
        _require(isinstance(group, dict), f"groups[{index}] is not an object")
        _require(bool(group.get("group_id")), f"groups[{index}] has no group_id")

    return document


__all__ = [
    "DOCUMENT_VERSION",
    "GENERATOR",
    "GROUP_FIELDS",
    "USER_FIELDS",
    "ExportImportError",
    "Result",
    "validate",
]
