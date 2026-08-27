"""What this layer answers for core.

Core has three questions whose answer changes when this layer is installed:
where a user's Profile is, which picture represents them, and where a picture
should be stored. It may not import this package to ask -- the import-linter
contract forbids it, and the reason is that core has to run without it -- so
it declares
:class:`~pas.plugins.identity.core.interfaces.IProfileSupport` and looks up
whatever provides it. This is that.

The dependency points the way the contract wants: this layer imports core,
core imports nothing of this. It is the same shape the back-channel logout
uses to reach the ``[server]`` layer.
"""

from pas.plugins.identity.content.catalog import query_catalog
from pas.plugins.identity.content.completeness import INCOMPLETE
from pas.plugins.identity.content.gate import enforcing
from pas.plugins.identity.content.subscribers import get_profile
from pas.plugins.identity.content.subscribers import remember_picture_url
from pas.plugins.identity.content.subscribers import remembered_picture_url
from pas.plugins.identity.core.interfaces import IProfileSupport
from plone.namedfile.file import NamedBlobImage
from zope.interface import implementer
from zope.lifecycleevent import modified


#: Filename given to a picture fetched from a provider.
#:
#: A provider's avatar URL rarely ends in something usable, and the field
#: needs *a* name. What it is called matters only in a download header.
PROVIDER_FILENAME = "portrait"


@implementer(IProfileSupport)
class ProfileSupport:
    """Answer core's questions about Profiles."""

    def profile_url(self, userid: str) -> str | None:
        """Return the URL of a user's Profile.

        :param userid: Canonical Plone userid.
        :returns: The absolute URL, or ``None`` when the user has none.
        """
        profile = get_profile(userid)
        return profile.absolute_url() if profile is not None else None

    def incomplete_profile_url(self, userid: str) -> str | None:
        """Return where a user must go to finish their profile, if anywhere.

        Answered from a catalog brain and from the same registry record the
        gate reads, so the authorization endpoint asking this on every request
        costs no object load and cannot disagree with the rest of the flow.

        Honours the enforcement switch. A site that has turned the gate off
        has said that an incomplete profile is a suggestion, and an
        authorization endpoint refusing to proceed would not be a suggestion.

        :param userid: Canonical Plone userid.
        :returns: The absolute URL of the edit form, or ``None``.
        """
        if not enforcing():
            return None
        catalog = query_catalog()
        if catalog is None:
            return None
        brains = catalog.unrestrictedSearchResults(userid=userid)
        if not brains:
            return None
        brain = brains[0]
        if brain.review_state != INCOMPLETE:
            return None
        return f"{brain.getURL()}/edit"

    def picture_url(self, userid: str) -> str | None:
        """Return the URL of the picture held on a user's Profile.

        :param userid: Canonical Plone userid.
        :returns: An absolute URL, or ``None`` when there is no Profile or it
            has no picture. ``None`` is what makes the member portrait the
            fallback, so it has to mean "nothing here" rather than "no
            Profile".
        """
        profile = get_profile(userid)
        if profile is None or getattr(profile, "image", None) is None:
            return None
        # `@@images` rather than `@@download` so a caller may ask for a scale.
        return f"{profile.absolute_url()}/@@images/image"

    def store_provider_picture(self, userid: str, data: bytes, url: str) -> bool:
        """Store a provider's avatar on a user's Profile, if it may.

        Refused when the user has a picture the provider did not put there.
        That is the precedence this layer has always claimed -- a picture
        somebody chose beats one a provider supplied -- and it is enforced
        the same way the text fields are: the Profile remembers what the
        provider last wrote, and the provider may replace only that.

        Refusing is not an error. The caller stores the member portrait
        instead, which is where it went before this layer existed, so a user
        who chose their own Profile picture still gets their provider's
        avatar kept as the fallback nobody sees.

        :param userid: Canonical Plone userid.
        :param data: The image bytes, already fetched and vetted.
        :param url: The claim they came from.
        :returns: Whether it was stored.
        """
        profile = get_profile(userid)
        if profile is None:
            return False

        current = getattr(profile, "image", None)
        if current is not None and not remembered_picture_url(profile):
            # Theirs. Untouched, and the provider does not acquire it by
            # being the next writer.
            return False

        profile.image = NamedBlobImage(
            data=data,
            contentType=_content_type(data),
            filename=PROVIDER_FILENAME,
        )
        remember_picture_url(profile, url)
        # The Profile is catalogued, and this layer reads users out of the
        # catalog; a write nobody reindexed is a write nobody can see.
        modified(profile)
        return True


def _content_type(data: bytes) -> str:
    """Return the image's media type, read from the bytes themselves.

    Not from the response header the fetch saw: core already refused
    anything whose header did not claim to be an image, and what is stored
    should be described by what it *is*. An unrecognised image is stored as
    a generic one rather than refused -- core vetted it, and a picture the
    browser can render is not worth losing to a signature table.

    :param data: The image bytes.
    :returns: A media type.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


__all__ = ["ProfileSupport"]
