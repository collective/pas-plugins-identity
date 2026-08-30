"""Keeping the credential out of the version repository.

Both principal types are versionable, which is worth having: a Profile is the
record of a person, and "who changed this and to what" is a question sites ask
about people more often than about pages.

It also reopens the one question the password behavior was designed around.
:mod:`pas.plugins.identity.core.behaviors.password` keeps the hash in an
annotation rather than in a Dexterity field, on the reasoning that an
annotation is invisible to serialization, GenericSetup export, the catalog and
versioning alike. Three of those four are true. The fourth is not:
CMFEditions deep-copies ``__annotations__`` into the snapshot, so with
versioning switched on every password change would leave the previous hash
behind in ``portal_repository``, where a revert would put it back and anyone
who can read history could read it.

That is worse than a field would have been. A field at least announces itself;
this would have been a credential accumulating somewhere nobody thinks to
look, defeating a password change without any sign that it had.

So the annotation is skipped on the way in and kept from the working copy on
the way out. The mechanism is the one ``SkipParentPointers`` uses: the pickler
asks ``persistent_id`` about every object it is about to write, and anything
answered for is stored as a reference rather than copied. Answering for the
credential mapping means the snapshot never contains it.

The modifier is registered whether or not the password behavior is enabled on
any type. It costs one dictionary lookup per save, and registering it only
when the behavior is on would mean a site that enables the behavior later
starts writing credentials into its history with nothing to notice.
"""

from Acquisition import aq_base
from pas.plugins.identity.core.behaviors.password import ANNOTATION_KEY
from Products.CMFEditions.interfaces.IModifier import ICloneModifier
from Products.CMFEditions.interfaces.IModifier import ISaveRetrieveModifier
from Products.CMFEditions.Modifiers import ConditionalModifier
from zope.annotation.interfaces import IAnnotations
from zope.interface import implementer


#: Id the modifier is registered under in ``portal_modifier``.
MODIFIER_ID = "SkipIdentityCredential"

#: Shown in the ZMI beside the standard modifiers.
MODIFIER_TITLE = "Keep pas.plugins.identity's password hash out of versions."


@implementer(ICloneModifier, ISaveRetrieveModifier)
class SkipCredentialAnnotation:
    """Leave the password annotation out of a version, both ways."""

    def getOnCloneModifiers(self, obj):
        """Answer for the credential mapping so the pickler writes a reference.

        :param obj: The object about to be versioned.
        :returns: ``(persistent_id, persistent_load, [], [])``, or ``None``
            when this object holds no credential and there is nothing to skip.
        """
        annotations = IAnnotations(obj, None)
        stored = None if annotations is None else annotations.get(ANNOTATION_KEY)
        if stored is None:
            return None

        target = id(aq_base(stored))

        def persistent_id(candidate):
            """Report whether this is the mapping to skip.

            :param candidate: An object the pickler is about to write.
            :returns: True for the credential mapping, otherwise None.
            """
            if id(aq_base(candidate)) == target:
                return True
            return None

        def persistent_load(reference):
            """Put nothing in its place.

            :param reference: What :func:`persistent_id` answered.
            :returns: None, always.
            """
            return None

        return persistent_id, persistent_load, [], []

    def beforeSaveModifier(self, obj, clone):
        """Do nothing; the pickler has already left the credential out.

        :param obj: The working copy.
        :param clone: The clone being stored.
        :returns: The empty answer this interface expects.
        """
        return {}, [], []

    def afterRetrieveModifier(self, obj, repo_clone, preserve=()):
        """Give the retrieved version the *working copy's* credential.

        A retrieved version holds ``None`` where the hash would be, because
        the save skipped it. Reverting to it would therefore clear the
        password rather than restore an old one -- which is not obviously
        wrong, but it is a silent account lockout, and history is not where a
        site should be deciding that. The current credential is carried across
        instead, so a revert restores the Profile and leaves the way in alone.

        :param obj: The working copy.
        :param repo_clone: The version being retrieved.
        :param preserve: Unused; part of the interface.
        :returns: The empty answer this interface expects.
        """
        if obj is None:
            return [], [], {}

        working = IAnnotations(obj, None)
        stored = None if working is None else working.get(ANNOTATION_KEY)
        clone_annotations = IAnnotations(repo_clone, None)
        if clone_annotations is None:
            return [], [], {}

        if stored is None:
            clone_annotations.pop(ANNOTATION_KEY, None)
        else:
            clone_annotations[ANNOTATION_KEY] = stored

        return [], [], {}


def register_modifier(portal_modifier) -> bool:
    """Register the modifier, once, at the front of the chain.

    Wrapped in a ``ConditionalModifier`` because the registry is an object
    manager: what it stores has to be persistent, and the standard modifiers
    are registered the same way. It is created disabled, like all of them,
    and switched on here -- a modifier nothing enables is registered and
    inert, which for this one would mean writing credentials into history
    while the ZMI showed the guard present.

    :param portal_modifier: The site's ``portal_modifier`` tool.
    :returns: Whether it was registered now, as opposed to already being there.
    """
    if MODIFIER_ID in portal_modifier.objectIds():
        return False
    wrapper = ConditionalModifier(
        MODIFIER_ID, SkipCredentialAnnotation(), MODIFIER_TITLE
    )
    # Ahead of the standard modifiers: they clone annotations wholesale, and
    # this one decides what is not there to be cloned.
    portal_modifier.register(MODIFIER_ID, wrapper, pos=0)
    # Registered modifiers arrive disabled, and a disabled one is inert --
    # which here would mean the guard present in the ZMI and credentials
    # going into history anyway.
    portal_modifier.edit(MODIFIER_ID, enabled=True)
    return True


def unregister_modifier(portal_modifier) -> bool:
    """Remove the modifier again.

    Called from the uninstall handler. The guard exists only to protect this
    package's annotation, so a site without this package has nothing for it
    to do -- and a persistent object whose class has gone with the package is
    a ``Broken`` one, which CMFEditions tolerates but nobody enjoys finding.

    Profiles and their history are left exactly where they are, on the same
    reasoning as everything else in the uninstall: removing an add-on is a
    configuration change, not an instruction to delete anybody's account.
    Nothing already written to history is affected, because it was written
    while the guard was in place.

    :param portal_modifier: The site's ``portal_modifier`` tool.
    :returns: Whether it was there to remove.
    """
    if MODIFIER_ID not in portal_modifier.objectIds():
        return False
    portal_modifier.manage_delObjects([MODIFIER_ID])
    return True
