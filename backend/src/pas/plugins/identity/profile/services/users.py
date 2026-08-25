"""``PATCH @users/<id>`` -- write a portrait to the Profile that owns it.

The ``[profile]`` layer decided that a user's picture lives on their Profile
and that the member portrait is the fallback -- see
:func:`pas.plugins.identity.core.serializer.portrait_of`, which is the read
side of that decision. Only the read side existed: a portrait uploaded
through user preferences went to ``portal_memberdata`` like any other, so a
site running this layer stored the picture in the place the reader looks at
*second* and then showed the Profile's empty field in preference to it. The
symptom is an upload that appears to work and changes nothing.

This closes it at the one seat the write passes through.
``plone.restapi``'s own ``@users`` PATCH is subclassed rather than reached
around, so everything else about updating a user -- passwords, login names,
the permission checks, the error bodies -- stays exactly what the rest of
Plone does; the single overridden method is where the bytes land.

Registered for :class:`~pas.plugins.identity.profile.interfaces.IIdentityProfileLayer`,
so a site without this optional layer keeps stock behaviour and there is no
Profile to be authoritative in the first place.
"""

from io import BytesIO
from pas.plugins.identity.profile.subscribers import get_profile
from pas.plugins.identity.profile.subscribers import remember_picture_url
from plone.namedfile.file import NamedBlobImage
from plone.restapi.services.users.update import UsersPatch
from Products.PlonePAS.utils import scale_image
from zope.lifecycleevent import modified

import codecs


class ProfileUsersPatch(UsersPatch):
    """Update a user, storing the portrait wherever that user's picture lives.

    Carries an explicit ``__init__`` for the reason
    :class:`~pas.plugins.identity.core.services.base.IdentityService` does:
    ``plone.rest`` mixes ``BrowserView`` into the class it publishes, so the
    registered service is constructible either way, while the factory class
    on its own is not -- and a service that cannot be constructed directly
    cannot be tested without standing up the publisher. The base class's own
    ``__init__`` delegates to a ``plone.rest`` base that has none.
    """

    def __init__(self, context, request) -> None:
        """Bind the service to its context and request.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        self.context = context
        self.request = request
        # What the base class's ``__init__`` sets: the traversal segments,
        # which is how ``@users/<id>`` knows which user it is about.
        self.params = []

    def set_member_portrait(self, user, portrait) -> None:
        """Store the portrait on the user's Profile, or fall back to the member.

        A user with no Profile -- the site's own ``admin``, an account
        created before this layer was installed -- is handled by the base
        class exactly as before. Nothing migrates a portrait between the two
        stores: which one answers for a user is decided by whether they have
        a Profile, and that does not change under them.

        :param user: The PAS user being updated.
        :param portrait: ``plone.restapi``'s portrait mapping, or ``None`` to
            remove the picture.
        """
        profile = get_profile(user.getId())
        if profile is None:
            super().set_member_portrait(user, portrait)
            return

        if portrait is None:
            if getattr(profile, "picture", None) is not None:
                profile.picture = None
                # Nothing there for a provider to own any more either.
                remember_picture_url(profile, "")
                modified(profile)
            return

        profile.picture = _as_image(portrait)
        # This picture is theirs, so a provider may not replace it at the
        # next login. Handing ownership back is what turns "the provider put
        # this here" into "the user chose this".
        remember_picture_url(profile, "")
        # The Profile is catalogued, and this layer reads users out of the
        # catalog; a write nobody reindexed is a write nobody can see.
        modified(profile)


def _as_image(portrait: dict) -> NamedBlobImage:
    """Turn ``plone.restapi``'s portrait mapping into a stored image.

    The decoding is the base class's, kept identical on purpose: the same
    request body has to mean the same bytes whichever store answers, or a
    site would get a different picture depending on an unrelated layer.

    :param portrait: Mapping with ``data`` and optionally ``encoding``,
        ``content-type``, ``filename`` and ``scale``.
    :returns: The image to assign to the Profile's ``picture`` field.
    """
    data = portrait.get("data")
    if isinstance(data, str):
        data = data.encode("utf-8")
    if "encoding" in portrait:
        data = codecs.decode(data, portrait["encoding"])
    if portrait.get("scale", False):
        # Only when asked. Volto crops and scales before uploading, and
        # scaling an already-scaled image a second time is how a portrait
        # comes out soft.
        data, _mimetype = scale_image(BytesIO(data))

    return NamedBlobImage(
        data=data,
        contentType=portrait.get("content-type", "application/octet-stream"),
        filename=portrait.get("filename") or "portrait",
    )


__all__ = ["ProfileUsersPatch"]
