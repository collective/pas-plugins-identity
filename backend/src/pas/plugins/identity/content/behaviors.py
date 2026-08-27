"""Keeping a user's password with the rest of the user.

Off unless a site turns it on, and the default is the other way round for a
reason worth stating before the code.

**Why this is opt-in.** Without it a new user's password goes to
``source_users``, which has held Plone's passwords for twenty years and has
been looked at accordingly. Moving a credential onto a content object takes
on four questions that a Dexterity *field* would answer wrongly by default:
``plone.restapi`` serializes fields, GenericSetup exports them, the catalog
can index them, and versioning snapshots them. Each is a separate path, each
fails by disclosing the credential, and each has to be remembered
independently.

**So the hash is an annotation, not a field.** An annotation is invisible to
all four without anything being excluded anywhere -- the difference between
"we remembered in four places" and "there is nothing to remember". Nothing
renders it, nothing exports it, and reading it takes an explicit accessor.

**What it buys.** A site whose users are content gets one object per person
holding everything about them, and Profile workflow becomes account
suspension: a ``deactivated`` Profile stops authenticating, which
``source_users`` cannot do at all.

**What it does not do.** It never migrates anything. A user whose credential
is already in ``source_users`` keeps it, and both stores answer -- turning
this on changes where the *next* password is written, not where the existing
ones are. Anything else would move credentials around behind an operator's
back.

Hashing is ``AccessControl.AuthEncoding``, which is what the rest of Plone
uses, so the stored form is one the stack already understands and no crypto
is invented here.
"""

from AccessControl.AuthEncoding import pw_encrypt
from AccessControl.AuthEncoding import pw_validate
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import ICredentialStorage
from pas.plugins.identity.core.interfaces import IUserContent
from persistent.mapping import PersistentMapping
from zope.annotation.interfaces import IAnnotations
from zope.component import adapter
from zope.interface import implementer


#: Annotation key. Namespaced, because an annotation store is shared with
#: every other adapter on the object.
ANNOTATION_KEY = "pas.plugins.identity.password"


@implementer(ICredentialStorage)
@adapter(IUserContent)
class PasswordStorage:
    """Store and check a password on the object it belongs to.

    Registered as a behavior *providing* core's
    :class:`~pas.plugins.identity.core.interfaces.ICredentialStorage`, so
    ``ICredentialStorage(obj, None)`` answers on a type where a site enabled
    it and returns ``None`` everywhere else. That ``None`` is what makes core
    fall back to ``source_users`` without knowing this module exists.
    """

    def __init__(self, context) -> None:
        """Bind to the object whose password this is.

        :param context: The content object.
        """
        self.context = context

    @property
    def _store(self) -> PersistentMapping:
        """Return the annotation this password lives in, creating it once.

        :returns: The mapping.
        """
        annotations = IAnnotations(self.context)
        if ANNOTATION_KEY not in annotations:
            annotations[ANNOTATION_KEY] = PersistentMapping()
        return annotations[ANNOTATION_KEY]

    def set_password(self, password: str) -> None:
        """Store a password, hashed.

        An empty password clears the entry rather than storing a hash of
        nothing: an externally authenticated user has no password, and a
        stored hash of the empty string is a credential somebody can guess.

        :param password: The plaintext, as PAS was given it.
        """
        if not password:
            self._store.pop("hash", None)
            return
        self._store["hash"] = pw_encrypt(password)

    def check_password(self, password: str) -> bool:
        """Report whether a password matches the stored one.

        :param password: The plaintext to check.
        :returns: Whether it matches. False when nothing is stored, so an
            account that has never had a password here cannot be signed in
            to with an empty one.
        """
        stored = self._store.get("hash")
        if not stored or not password:
            return False
        try:
            return bool(pw_validate(stored, password))
        except (ValueError, TypeError):  # pragma: no cover - corrupt storage
            logger.warning("Unreadable password hash on %r", self.context)
            return False


def clear_on_copy(obj, event) -> None:
    """Drop the password from a copied object.

    Copy and paste on a content object is a normal thing to do to content.
    Doing it to a user must not hand the copy somebody else's credential, and
    an annotation is copied with everything else unless something removes it.

    Registered for every ``IUserContent`` rather than only where the behavior
    is enabled: a site that turns it off still has the annotations it wrote,
    and a copy must not resurrect one.

    :param obj: The new copy.
    :param event: The copy event.
    """
    annotations = IAnnotations(obj)
    if ANNOTATION_KEY in annotations:
        del annotations[ANNOTATION_KEY]
        logger.info("Cleared the copied password on %r", obj)


__all__ = [
    "ANNOTATION_KEY",
    "PasswordStorage",
    "clear_on_copy",
]
