"""The ``Profile`` content type.

One Profile per canonical userid. The fields are exactly the PAS property
sheet the ``[profile]`` layer's PAS plugin serves, which is why they are listed
here rather than borrowed from a Dublin Core behavior: every one of them
becomes catalog *metadata*, and metadata that nobody serves is dead weight in
every brain.

``userid`` is the join to :mod:`pas.plugins.identity.core.store` and is
permanent -- an identity, a local role assignment and a catalog entry all
point at it, and changing it silently detaches every one of them. Three
things keep it that way, because there are three ways to write a field:

* the edit form renders it read-only, so nobody retypes it by hand;
* :class:`~pas.plugins.identity.profile.deserializer.UseridIsPermanent`
  refuses a change over the REST API with a 400 rather than a traceback;
* :mod:`pas.plugins.identity.profile.doctor` treats a duplicate as an error
  rather than a merge, for the ones that got in before any of this.

``email`` is required. A Profile exists to be the thing a person is reached
and recognised by, and the enumeration plugin, the property map and the
magic-link join all read it; a Profile without one is a record that cannot
do its job.

``image`` is where this layer *does* own the user's image, and it wins over
the member portrait when it is set -- see
:func:`pas.plugins.identity.core.serializer.portrait_of` for the precedence
and why it runs that way round. It is not in
:data:`~pas.plugins.identity.profile.pas.PROPERTY_FIELDS`: those are served
from catalog metadata, and a blob has no business in a brain.
"""

from pas.plugins.identity import _
from pas.plugins.identity.core.interfaces import IUserContent
from plone.autoform.directives import mode
from plone.autoform.directives import read_permission
from plone.autoform.directives import write_permission
from plone.dexterity.content import Container
from plone.namedfile.field import NamedBlobImage
from plone.supermodel import model
from z3c.form.interfaces import IEditForm
from zope import schema
from zope.interface import implementer


class IProfileSchema(model.Schema, IUserContent):
    """Schema of the Profile content type.

    Extends :class:`~pas.plugins.identity.core.interfaces.IUserContent`,
    which is how core knows objects of this type are users and may create
    them. The three attributes that interface promises -- ``userid``,
    ``login`` and ``group_ids`` -- are declared below and were already here;
    claiming the marker states the contract rather than adding to it.

    The fourth clause is about placement rather than fields: the object's id
    within its container is the userid. That is what
    :func:`~pas.plugins.identity.profile.subscribers._profile_id` has always
    returned, for its own reason -- an opaque userid never changes, so the
    object never has to be renamed and no bookmark is ever stranded.
    """

    userid = schema.TextLine(
        title=_("User ID"),
        description=_(
            "The canonical Plone user id this profile belongs to. "
            "Assigned once and never changed."
        ),
        required=True,
    )

    login = schema.TextLine(
        title=_("Login name"),
        description=_("The name this user logs in with."),
        required=True,
    )

    fullname = schema.TextLine(
        title=_("Full name"),
        required=False,
    )

    email = schema.TextLine(
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
            "Ids of the groups this user belongs to. Editing this field is "
            "the only way membership changes; there is no write API."
        ),
        value_type=schema.TextLine(),
        required=False,
        missing_value=(),
        default=(),
    )
    # Shown, never editable: an edit form offering it is an invitation to
    # detach a Profile from the identity it belongs to. The add form still
    # asks, because that is the one moment the answer is not yet decided.
    mode(IEditForm, userid="display")

    write_permission(
        userid="pas.plugins.identity.profile.edit",
        login="pas.plugins.identity.profile.edit",
        fullname="pas.plugins.identity.profile.edit",
        email="pas.plugins.identity.profile.edit",
        home_page="pas.plugins.identity.profile.edit",
        description="pas.plugins.identity.profile.edit",
        location="pas.plugins.identity.profile.edit",
        image="pas.plugins.identity.profile.edit",
        group_ids="pas.plugins.identity.profile.edit",
    )
    read_permission(
        userid="pas.plugins.identity.profile.view",
        login="pas.plugins.identity.profile.view",
        fullname="pas.plugins.identity.profile.view",
        email="pas.plugins.identity.profile.viewpii",
        home_page="pas.plugins.identity.profile.view",
        description="pas.plugins.identity.profile.view",
        location="pas.plugins.identity.profile.view",
        image="pas.plugins.identity.profile.view",
        group_ids="pas.plugins.identity.profile.view",
    )


@implementer(IProfileSchema)
class Profile(Container):
    """A Profile.

    Folderish so that a deployment can file per-user content underneath it --
    a portrait, an attachment, a personal folder -- without needing a second
    content type. Nothing in this layer puts anything inside one.
    """

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
