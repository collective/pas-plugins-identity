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

``email`` is required. A Profile exists to be the thing a person is reached
and recognised by, and the enumeration plugin, the property map and the
magic-link join all read it; a Profile without one is a record that cannot
do its job.

``image`` is where a user's picture lives, and it wins over the member
portrait when it is set -- see
:func:`pas.plugins.identity.core.serializer.portrait_of` for the precedence
and why it runs that way round. It is not in
:data:`~pas.plugins.identity.core.pas.profile.PROPERTY_FIELDS`: those are served
from catalog metadata, and a blob has no business in a brain.
"""

from pas.plugins.identity import _
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IUserContent
from pas.plugins.identity.core.vocabularies.groups import GROUPS_VOCABULARY
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
    them. The three attributes that interface promises -- ``userid``,
    ``login`` and ``group_ids`` -- are declared below and were already here;
    claiming the marker states the contract rather than adding to it.

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

    email = Email(
        title=_("Email"),
        description=_("Required: this is what the user is reached and matched by."),
        required=True,
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

    group_ids = schema.Tuple(
        title=_("Groups"),
        description=_(
            "The groups this user belongs to. Membership is kept on the "
            "member rather than on the group, so editing this field and "
            "calling api.group.add_user are two ways to the same place."
        ),
        # A vocabulary rather than free text. The value is a group id and
        # nothing checked that it named a group: the groups plugin filters an
        # unknown id out rather than failing, so a typo produced a membership
        # that silently granted nothing.
        value_type=schema.Choice(vocabulary=GROUPS_VOCABULARY),
        required=False,
        missing_value=(),
        default=(),
    )
    write_permission(
        login="pas.plugins.identity.content.edit",
        fullname="pas.plugins.identity.content.edit",
        email="pas.plugins.identity.content.edit",
        home_page="pas.plugins.identity.content.edit",
        description="pas.plugins.identity.content.edit",
        location="pas.plugins.identity.content.edit",
        image="pas.plugins.identity.content.edit",
        # Not ``.edit``: see permissions.zcml. The owner of a profile holds
        # the edit permission on it, and this field is what grants roles.
        group_ids="pas.plugins.identity.content.editgroups",
    )
    read_permission(
        login="pas.plugins.identity.content.view",
        fullname="pas.plugins.identity.content.view",
        email="pas.plugins.identity.content.viewpii",
        home_page="pas.plugins.identity.content.view",
        description="pas.plugins.identity.content.view",
        location="pas.plugins.identity.content.view",
        image="pas.plugins.identity.content.view",
        group_ids="pas.plugins.identity.content.view",
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
