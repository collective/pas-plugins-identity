"""``@users`` and ``@portrait``, pointed at the Profile that owns the picture.

A user's picture lives on their Profile
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

``GET @portrait/<id>`` is the same decision on the other side, and it was
missing for longer. That endpoint reads ``getPersonalPortrait``, which only
ever sees ``portal_memberdata``, so it answered 404 for a user whose picture
was on their Profile. It matters more than a missing image on a page: it is
the URL the ``[server]`` layer publishes as the OIDC ``picture`` claim, and a
relying party fetches it server to server. A 404 there is a federation that
silently loses everybody's photograph.

``@portrait`` is public, and serving a Profile's picture through it makes
that picture publicly readable at a stable URL even when the Profile itself
is not -- ``incomplete`` Profiles are not anonymously viewable, and the image
field carries a read permission. That is deliberate and it is what the member
portrait has always done: a portrait is the one part of a user record Plone
publishes, and a claim a relying party cannot fetch is not a claim. The
Profile's own URL is never handed out, so this discloses no more than stock
Plone did.

Registered for this package's own browser layer, so a site that has not
installed it keeps stock behaviour.
"""

from io import BytesIO
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.core.subscribers import remember_picture_url
from plone import api
from plone.namedfile.file import NamedBlobImage
from plone.namedfile.utils import stream_data
from plone.restapi.services.users.get import PortraitGet
from plone.restapi.services.users.update import UsersPatch
from Products.PlonePAS.utils import decleanId
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
            if getattr(profile, "image", None) is not None:
                profile.image = None
                # Nothing there for a provider to own any more either.
                remember_picture_url(profile, "")
                modified(profile)
            return

        profile.image = _as_image(portrait)
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
    :returns: The image to assign to the Profile's ``image`` field.
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


class ProfilePortraitGet(PortraitGet):
    """Serve a user's picture from their Profile, or from the member.

    The read counterpart of :class:`ProfileUsersPatch`, and the same
    precedence: the Profile answers when it has a picture, and everything
    else falls through to ``plone.restapi``'s own implementation, which
    covers the users this layer does not serve -- the site's ``admin``, an
    account created before the layer was installed, anyone with no Profile.

    Carries an explicit ``__init__`` for the same reason
    :class:`ProfileUsersPatch` does, and sets what the base class's own
    ``__init__`` sets: ``plone.rest`` mixes ``BrowserView`` into the class it
    publishes, so the registered service is constructible either way while
    the factory class on its own is not.
    """

    def __init__(self, context, request) -> None:
        """Bind the service to its context and request.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        self.context = context
        self.request = request
        self.params = []
        self.portal = api.portal.get()
        self.portal_membership = api.portal.get_tool("portal_membership")

    def render(self):
        """Return the picture bytes, or defer to the base implementation.

        ``Content-Length`` is set here rather than left to the publisher.
        ``stream_data`` answers with the bytes for an image whose blob is
        still uncommitted and with a ``filestream_range_iterator`` once it is
        on disk, and the publisher can only measure the first: it calls
        ``len()`` on whatever it is handed, so a stored picture -- every one
        that matters, in a running site -- came back as a 500 while a test
        that had just set the field passed. Length is the one thing this has
        to say for itself.

        :returns: The streamed image, or whatever the base class returns
            when no Profile holds a picture for this user.
        """
        image = self._profile_image()
        if image is None:
            return super().render()

        self.request.response.setStatus(200)
        self.request.response.setHeader("Content-Type", image.contentType)
        self.request.response.setHeader("Content-Length", image.getSize())
        return stream_data(image)

    def _profile_image(self):
        """Return the picture held on this request's user's Profile.

        Reads the same ``params`` the base class does, including the empty
        case that means "my own portrait", so the two implementations cannot
        disagree about which user is being asked for.

        :returns: The image, or ``None`` when there is no Profile or it has
            no picture.
        """
        if len(self.params) == 1:
            userid = decleanId(self.params[0])
        elif not self.params:
            userid = self.portal_membership.getAuthenticatedMember().getId()
        else:
            # Let the base class raise: the message is its to write, and
            # duplicating it here is a second thing to keep in step.
            return None

        profile = get_profile(userid)
        return None if profile is None else getattr(profile, "image", None)
