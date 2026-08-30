"""What a login writes into the transaction's own record.

Zope already writes something. ``ZPublisher.utils.recordMetaData`` sets the
transaction's description to the physical path of the published object and its
user to whoever was authenticated -- but it runs **after traversal and before
the view is called**, and on a login the view is where authentication happens.
So a federated sign-in used to commit as ``/plone/@identity-callback`` with no
user at all: the one transaction that creates an account, writes several
hundred objects and joins a person to a userid was the one transaction the
undo log could say nothing about.

This module is what says something. ``Transaction.note`` appends rather than
replaces, so what Zope wrote stays and each fact below is added as its own
line:

.. code-block:: text

   /plone/@identity-callback
   identity: login 8f2c1e... via github (new user, new identity)
   identity: profile created at /plone/users/8f2c1e...

**No claims, no email address, no provider subject.** The note is written to a
place that is never purged short of packing the storage, which makes it the
worst possible home for personal data -- the same argument that keeps the IP
address out of an audit entry unless a site opts in. The userid is opaque and
the provider id is site configuration, so neither identifies anybody on its
own. For an externally authenticated user the userid *is* the login, which is
what ``IdentityPlugin.authenticateCredentials`` returns; a local password
login notes the login name the person typed, which they chose and which the
access log already carries.

**Nothing here joins the transaction.** A note and a user are attributes of the
``Transaction`` object rather than of any resource manager, so annotating a
request that wrote nothing leaves it writing nothing. There is a test that says
so, because the opposite -- an audit trail that turns every read into a write --
would be a bad trade made silently.
"""

from plone import api
from plone.api.exc import CannotGetPortalError

import transaction


#: Prefix every line this package adds, so an operator reading an undo log can
#: tell our lines from Zope's path and from any other package's notes.
PREFIX = "identity:"


def note(text: str) -> None:
    """Append one line to the current transaction's description.

    :param text: The line, without the package prefix.
    """
    transaction.get().note(f"{PREFIX} {text}")


def _attributed(txn: transaction.Transaction) -> bool:
    """Report whether the transaction already names a real user.

    ``recordMetaData`` writes ``"<path> None"`` for an anonymous request --
    the string, not the value -- so an empty user field is not the only way
    to be unattributed.

    :param txn: The transaction.
    :returns: Whether its user field names somebody.
    """
    user = (txn.user or "").strip()
    if not user:
        return False
    # The field is "<path> <userid>"; a path with no userid is not attribution.
    return user.rsplit(" ", 1)[-1] not in ("", "None")


def attribute_to(userid: str) -> None:
    """Record the transaction as this user's, unless it already names one.

    The person signing in is who the transaction is *for*, and at traversal
    time they were anonymous. Guarded rather than unconditional so that a
    request which really was made by somebody else -- an administrator linking
    an identity on another person's behalf -- keeps its own attribution.

    :param userid: Canonical Plone userid.
    """
    txn = transaction.get()
    if _attributed(txn):
        return
    try:
        path = api.portal.get().getId()
    except (
        CannotGetPortalError,
        AttributeError,
    ):  # pragma: no cover - a login outside a site
        path = ""
    txn.setUser(userid, path)


def note_login(
    userid: str,
    provider: str = "",
    is_new_user: bool = False,
    is_new_identity: bool = False,
    login: str = "",
) -> None:
    """Record that this transaction signed somebody in.

    Attribution is always to the *userid*, whatever the note says: the userid
    is what a local role, an ownership and every other record in the site is
    written against, so it is the only thing an operator can join an undo
    entry back to. ``login`` changes the text, never the attribution.

    :param userid: Canonical Plone userid.
    :param provider: Provider id, empty for a login against a local password.
    :param is_new_user: Whether the userid was minted by this login.
    :param is_new_identity: Whether the external identity was linked by it.
    :param login: The login name offered, when it differs from the userid --
        which it does for a local password and does not for an external
        identity, where the plugin returns the userid as the login.
    """
    where = f" via {provider}" if provider else " with a local password"
    firsts = []
    if is_new_user:
        firsts.append("new user")
    if is_new_identity:
        firsts.append("new identity")
    suffix = f" ({', '.join(firsts)})" if firsts else ""
    named = f"{login} ({userid})" if login and login != userid else userid
    note(f"login {named}{where}{suffix}")
    attribute_to(userid)


def note_profile_created(profile) -> None:
    """Record that this transaction minted a Profile.

    Its own line rather than a flag on the login line: the Profile is created
    by a subscriber, which does not know what the plugin decided, and a
    consumer firing the event by hand creates one with no login at all.

    :param profile: The Profile just created.
    """
    note(f"profile created at {'/'.join(profile.getPhysicalPath())}")


__all__ = [
    "PREFIX",
    "attribute_to",
    "note",
    "note_login",
    "note_profile_created",
]
