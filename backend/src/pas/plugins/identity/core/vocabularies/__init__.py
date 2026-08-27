"""Vocabularies this package publishes, and who may read them."""

from plone.app.content.browser.vocabulary import PERMISSIONS


#: What a caller needs to read this package's vocabularies over
#: ``@vocabularies``.
#:
#: Not the default. ``plone.restapi`` serves a vocabulary under ``zope2.View``
#: unless it is named in the map below, which means anonymously on any public
#: site -- and both of ours describe the shape of the site's user records.
#: ``Groups`` is the one that made this worth doing: it lists every group on
#: the site by id and title, and the group map added it to a second widget.
#:
#: ``Modify portal content`` rather than a management permission, matching
#: what stock Plone puts on ``plone.app.vocabularies.Users``, which is the
#: closest analogue -- it also enumerates principals. A management permission
#: would be tighter, but these vocabularies are read by content forms as well
#: as by the control panel: the ``[content]`` layer's ``group_ids`` field is a
#: ``Choice`` over ``Groups``, and an editor who can edit a Profile has to be
#: able to fill that widget.
VOCABULARY_PERMISSION = "Modify portal content"

#: The vocabularies this package registers.
PUBLISHED = (
    "pas.plugins.identity.UserFields",
    "pas.plugins.identity.Groups",
)


def protect_vocabularies() -> None:
    """Require a permission to read this package's vocabularies.

    ``plone.restapi``'s ``@vocabularies`` service is published under
    ``zope2.View`` and consults
    :data:`plone.app.content.browser.vocabulary.PERMISSIONS` for anything
    stronger. That mapping is the documented extension point -- "thus
    vocabularies can be protected stronger than the default" -- so this
    registers into it rather than patching the service.

    Called from :mod:`pas.plugins.identity.core`. Idempotent.
    """
    for name in PUBLISHED:
        PERMISSIONS[name] = VOCABULARY_PERMISSION
