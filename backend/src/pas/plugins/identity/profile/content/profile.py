"""The ``Profile`` content type (§4.7).

One Profile per canonical userid. The fields are exactly the PAS property
sheet the ``[profile]`` layer serves in Gate 6b, which is why they are listed
here rather than borrowed from a Dublin Core behavior: every one of them
becomes catalog *metadata*, and metadata that nobody serves is dead weight in
every brain.

``userid`` is the join to :mod:`pas.plugins.identity.core.store` and is
permanent (I1). Nothing in this layer rewrites it; the field is marked
read-only after creation through the ``userid`` mode in the edit form, and the
consistency check in :mod:`pas.plugins.identity.profile.doctor` treats a
duplicate as an error rather than a merge.
"""

from pas.plugins.identity import _
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IProfileSchema(model.Schema):
    """Schema of the Profile content type."""

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
        required=False,
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

    group_ids = schema.Tuple(
        title=_("Groups"),
        description=_(
            "Ids of the groups this user belongs to. Editing this field is "
            "the only way membership changes; there is no write API (§7)."
        ),
        value_type=schema.TextLine(),
        required=False,
        missing_value=(),
        default=(),
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
