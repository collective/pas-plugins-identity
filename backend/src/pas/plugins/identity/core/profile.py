"""The ``UserProfile`` content type.

One Profile per canonical userid. The fields are exactly the PAS property
sheet :mod:`pas.plugins.identity.core.pas.profile` serves, which is why they
are listed here rather than borrowed from a Dublin Core behavior: every one of
them becomes catalog *metadata*, and metadata that nobody serves is dead
weight in every brain.

``userid`` is the join to :mod:`pas.plugins.identity.core.store` and is
permanent -- an identity, a local role assignment and a catalog entry all
point at it, and changing it silently detaches every one of them. Three
things keep it that way, because there are three ways to write a field:

* the edit form renders it read-only, so nobody retypes it by hand;
* the object id *is* the userid, so there is no separate field for a rename
  to disagree with -- see ``tests/core/test_derived_ids.py``;
* :mod:`pas.plugins.identity.core.doctor` treats a duplicate as an error
  rather than a merge, for the ones that got in before any of this.

``emails`` is required, and ``email`` is derived from it. A person has more
than one address, signs in with more than one of them, and which one is
theirs *here* is a question whose answer changes -- so the list is what is
stored and the single value everything else reads is computed: the first
verified address, or the first address at all. An address counts as verified
when this site holds an ``email`` identity for it, which is what a magic link
creates; see :mod:`pas.plugins.identity.core.emails`, which also says why
linking one reindexes the Profile.

``image`` is where a user's picture lives, and it wins over the member
portrait when it is set -- see
:func:`pas.plugins.identity.core.serializer.portrait_of` for the precedence
and why it runs that way round. It is not in
:data:`~pas.plugins.identity.core.pas.profile.PROPERTY_FIELDS`: those are served
from catalog metadata, and a blob has no business in a brain.
"""

from pas.plugins.identity import _
from pas.plugins.identity import logger
from pas.plugins.identity.core.emails import clean
from pas.plugins.identity.core.emails import normalize
from pas.plugins.identity.core.emails import preferred_address
from pas.plugins.identity.core.emails import verified_addresses
from pas.plugins.identity.core.interfaces import IUserContent
from plone.autoform.directives import read_permission
from plone.autoform.directives import write_permission
from plone.dexterity.content import Container
from plone.namedfile.field import NamedBlobImage
from plone.schema import Email
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IUserProfileSchema(model.Schema, IUserContent):
    """Schema of the UserProfile content type.

    Extends :class:`~pas.plugins.identity.core.interfaces.IUserContent`,
    which is how core knows objects of this type are users and may create
    them. Two of the three attributes that interface promises -- ``userid``
    and ``login`` -- are here; the third, ``group_ids``, comes from the
    :class:`~pas.plugins.identity.core.membership.IGroupMembership` behavior,
    which the FTI enables and which the Group type enables too. Claiming the
    marker states the contract rather than adding to it.

    The fourth clause is about placement rather than fields: the object's id
    within its container is the userid. That is what
    :func:`~pas.plugins.identity.core.subscribers._profile_id` has always
    returned, for its own reason -- an opaque userid never changes, so the
    object never has to be renamed and no bookmark is ever stranded.
    """

    login = schema.TextLine(
        title=_("Login name"),
        description=_("The name this user logs in with."),
        required=True,
    )

    fullname = schema.TextLine(
        title=_("Full name"),
        description=_(
            "Required: it is how this user is named everywhere the site "
            "shows them, and a provider is not obliged to send one."
        ),
        required=True,
    )

    emails = schema.Tuple(
        title=_("Email addresses"),
        description=_(
            "The addresses this person uses, most preferred first. At least "
            "one is required: a Profile exists to be the thing somebody is "
            "reached and recognised by. Adding an address here does not "
            "prove it -- verifying one sends a link to it, and only an "
            "address this site has verified can be used to sign in or to "
            "attach a new provider account to this one."
        ),
        value_type=Email(title=_("Email")),
        # ``required`` rather than ``min_length=1``: zope.schema validates a
        # field's default when the schema is defined, and a one-address
        # minimum with an empty default fails at import time. Required plus a
        # ``missing_value`` of ``()`` says the same thing -- an empty tuple is
        # missing, and a form insists on an entry.
        required=True,
        missing_value=(),
        default=(),
    )

    email = Email(
        title=_("Email"),
        description=_(
            "The address that stands for this person: the first verified one "
            "in the list above, or the first one at all when none is "
            "verified. Derived rather than typed, so there is no second "
            "value to disagree with the list."
        ),
        required=False,
        readonly=True,
    )

    home_page = schema.TextLine(
        title=_("Home page"),
        required=False,
    )

    description = schema.Text(
        title=_("Biography"),
        required=False,
    )

    location = schema.TextLine(
        title=_("Location"),
        required=False,
    )

    image = NamedBlobImage(
        title=_("Picture"),
        description=_(
            "Shown wherever this user is represented. When it is empty the "
            "portrait stored on the member is used instead, and failing that "
            "the user's initials."
        ),
        required=False,
    )

    write_permission(
        login="pas.plugins.identity.content.edit",
        fullname="pas.plugins.identity.content.edit",
        emails="pas.plugins.identity.content.edit",
        home_page="pas.plugins.identity.content.edit",
        description="pas.plugins.identity.content.edit",
        location="pas.plugins.identity.content.edit",
        image="pas.plugins.identity.content.edit",
    )
    read_permission(
        login="pas.plugins.identity.content.view",
        fullname="pas.plugins.identity.content.view",
        emails="pas.plugins.identity.content.viewpii",
        email="pas.plugins.identity.content.viewpii",
        home_page="pas.plugins.identity.content.view",
        description="pas.plugins.identity.content.view",
        location="pas.plugins.identity.content.view",
        image="pas.plugins.identity.content.view",
    )


@implementer(IUserProfileSchema)
class UserProfile(Container):
    """A user profile.

    Folderish so that a deployment can file per-user content underneath it --
    a portrait, an attachment, a personal folder -- without needing a second
    content type. Nothing in this layer puts anything inside one.
    """

    @property
    def userid(self) -> str:
        """Return the canonical userid, which is the object's own id.

        Computed rather than stored, and that is a correctness fix rather
        than tidiness. It used to be both: a required field *and* the id the
        object is filed under, with nothing keeping the two equal. They are
        read by different code -- :meth:`_content_user` traverses
        ``container.get(userid)`` while the catalog indexes the field -- so a
        rename left enumeration working and every write silently addressed to
        nothing. One value cannot disagree with itself.

        The schema no longer declares it, so no form offers it and no
        deserializer can set it; :class:`IUserContent` promises the
        *attribute*, which this is.

        :returns: The userid.
        """
        return self.getId()

    @userid.setter
    def userid(self, value: str) -> None:
        """Accept a write of the derived id, and discard it.

        Nothing may change this value -- it is the object's id -- but a
        great deal of code writes it: Dexterity's factory setattrs every
        keyword it is handed, and every payload exported before it became
        derived still carries the key. Raising would turn each of those into
        a failed creation or a failed import for a value that was already
        correct.

        A write that *disagrees* with the id is a different matter, and is
        logged: it is somebody trying to reassign a principal, which is
        exactly what this property exists to make impossible.

        :param value: The value being written, which is ignored.
        """
        if value and value != self.getId():
            logger.warning(
                "Ignoring an attempt to set a userid to %r on %r; it is "
                "derived from the object id",
                value,
                self.getId(),
            )

    @property
    def emails(self) -> tuple[str, ...]:
        """Return this person's addresses, in their own order.

        A property so that whatever writes the field -- the Dexterity
        factory, a PATCH, a claims sync -- stores the normalized form. What
        the catalog indexes and what a lookup compares against are then the
        same strings, which a case difference between two writes would
        otherwise quietly break.

        :returns: The addresses.
        """
        return getattr(self, "_emails", ())

    @emails.setter
    def emails(self, value: object) -> None:
        """Store a list of addresses, normalized and de-duplicated.

        :param value: The addresses as supplied.
        """
        self._emails = clean(value)

    @property
    def email(self) -> str:
        """Return the one address that stands for this person.

        Derived rather than stored: two values that have to agree, with
        nothing making them agree, is the shape that already cost this
        package a userid that could drift from its object id.

        :returns: The first verified address in :attr:`emails`, the first
            address at all when none is verified, and the empty string when
            there are none.
        """
        return preferred_address(self.getId(), self.emails)

    @email.setter
    def email(self, value: str) -> None:
        """Accept a write of the derived address by adding it to the list.

        A great deal of code writes ``email``: the Dexterity factory setattrs
        every keyword it is handed, the claims sync writes what a provider
        sent, and every payload exported before this became derived carries
        the key. Raising would turn each of those into a failed creation or a
        failed import.

        The address is moved to the front rather than appended, because the
        thing being written is *the* address -- and the fence that stops a
        login reordering a list its owner arranged is not here but in
        :func:`~pas.plugins.identity.core.subscribers.sync_claims`, which
        only writes while the current value is still exactly what the
        provider last put there. Once somebody edits their own list, or
        verifies an address that outranks the provider's, the derived value
        stops matching what was remembered and the provider is locked out of
        the field for good.

        An empty write is ignored rather than clearing the list: a provider
        that stops sending an address has not told us the person no longer
        has one, and an empty ``emails`` is an incomplete profile.

        :param value: The address being written.
        """
        address = normalize(value)
        if not address:
            return
        self.emails = (address, *(a for a in self.emails if a != address))

    @property
    def verified_emails(self) -> tuple[str, ...]:
        """Return the addresses this site has proved belong to this person.

        :returns: Those of :attr:`emails` with an ``email`` identity held for
            this userid, in the profile's own order.
        """
        return verified_addresses(self.getId(), self.emails)

    def Title(self) -> str:
        """Return the display title.

        The full name when there is one, the login otherwise; never empty, so
        that a Profile is identifiable in a listing before the user has filled
        anything in.

        :returns: The title.
        """
        return self.fullname or self.login or self.userid or ""

    def Description(self) -> str:
        """Return the description.

        :returns: The biography, or an empty string.
        """
        return self.description or ""
