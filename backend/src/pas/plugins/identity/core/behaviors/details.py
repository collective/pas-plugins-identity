"""The parts of a Profile a person fills in about themselves.

``home_page``, ``location`` and ``image`` used to be fields on the Profile
schema. Same fields and same storage -- a schema-only behavior stores its
attributes on the content object -- but they are now something a *type* opts
into, so a site running its own user type gets them without declaring three
fields and their permissions again.

**No fieldset directive, deliberately.** These stay on the default tab, beside
the login and the full name, because that is what a person opening their own
profile expects to edit: the whole of the ordinary form in one place. Only the
addresses earn a tab of their own, and only because they carry a different read
permission -- see :mod:`pas.plugins.identity.core.behaviors.email`.

**Two of these are member properties and one is not.** ``home_page`` and
``location`` are in
:data:`~pas.plugins.identity.core.pas.profile.PROPERTY_FIELDS`, so they are
served to PAS from catalog metadata and every template that asks Plone for
them gets an answer. ``image`` is not, and cannot be: those values are read off
a brain, and a blob has no business in one.

``image`` is where a user's picture lives, and it wins over the member portrait
when it is set -- see
:func:`pas.plugins.identity.core.portraits.picture_url` for the
precedence and why it runs that way round.

**And the fields only reach a form because of the last line of this module.**
Enabling a behavior on a type does not put its fields on a form: ``@types`` and
every autoform-built form ask for the behaviors marked ``IFormFieldProvider``
and skip the rest, silently.
"""

from pas.plugins.identity import _
from plone.autoform.directives import read_permission
from plone.autoform.directives import write_permission
from plone.autoform.interfaces import IFormFieldProvider
from plone.namedfile.field import NamedBlobImage
from plone.supermodel import model
from zope import schema
from zope.interface import provider


# What makes the fields appear on a form at all; see the module docstring.
# Applied here rather than as a ``provides=`` in ZCML because the marker
# belongs to the schema, and a schema that is a form field provider on one
# site and not on another is a difference nobody would think to look for.
@provider(IFormFieldProvider)
class IProfileDetails(model.Schema):
    """What a person says about themselves, and their picture."""

    home_page = schema.TextLine(
        title=_("Home page"),
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
        home_page="pas.plugins.identity.content.edit",
        location="pas.plugins.identity.content.edit",
        image="pas.plugins.identity.content.edit",
    )
    read_permission(
        home_page="pas.plugins.identity.content.view",
        location="pas.plugins.identity.content.view",
        image="pas.plugins.identity.content.view",
    )


__all__ = ["IProfileDetails"]
