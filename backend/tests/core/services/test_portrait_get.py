"""``GET @portrait/<id>`` -- reading a picture back out of whichever store holds it.

``plone.restapi``'s implementation reads ``getPersonalPortrait``, which only
ever sees ``portal_memberdata``. On a site running this layer that is the
*fallback* store, so the endpoint answered 404 for exactly the users whose
picture this layer had taken charge of.

That is worse than a missing image on a page. ``@portrait`` is the URL the
``[server]`` layer publishes as the OIDC ``picture`` claim, and a relying
party fetches it server to server with no credentials. A 404 there is a
federation that silently loses everybody's photograph -- and it fails as an
*omitted* claim rather than an error, so the downstream site cannot tell it
from a user who never uploaded one.

Found by running the real thing: the demo relying party stopped receiving
pictures the moment the identity provider started storing them in the right
place.
"""

from pas.plugins.identity.core.services.users import ProfilePortraitGet
from plone.namedfile.file import NamedBlobImage

import pytest


#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


def read(service) -> bytes:
    """Drain whatever the service returned into bytes.

    ``stream_data`` gives back a blob iterator for a stored image and a
    plain ``bytes`` for a small one, and which of the two a test sees is not
    something the test should care about.

    :param service: The rendered service's return value.
    :returns: The bytes.
    """
    if service is None:
        return b""
    if isinstance(service, bytes):
        return service
    return b"".join(service)


class TestAUserWithAProfilePicture:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")
        self.profile.image = NamedBlobImage(
            data=PNG, contentType="image/png", filename="me.png"
        )
        self.service = ProfilePortraitGet(portal, portal.REQUEST)
        self.service.params = ["alice"]

    def test_it_serves_the_profile_picture(self):
        """The bug: this answered 404, because the stock implementation only
        ever looks in ``portal_memberdata``."""
        body = read(self.service.render())

        assert body == PNG

    def test_it_answers_200(self):
        """An omitted OIDC claim and a broken one look identical downstream,
        so the status is worth asserting on its own."""
        self.service.render()

        assert self.service.request.response.getStatus() == 200

    def test_it_sends_the_stored_content_type(self):
        """A relying party refuses anything that does not claim to be an
        image, so a wrong content type is the same as no picture."""
        self.service.render()

        assert self.service.request.response.getHeader("Content-Type") == "image/png"

    def test_it_sends_the_content_length(self):
        """The publisher cannot work it out for itself.

        ``stream_data`` hands back the bytes while the blob is uncommitted
        and a ``filestream_range_iterator`` once it is on disk, and the
        publisher calls ``len()`` on what it gets. Without this header a
        picture that had actually been stored -- every one in a running site
        -- answered 500, while this suite, which sets the field and reads it
        back in the same transaction, saw bytes and passed.
        """
        self.service.render()

        length = self.service.request.response.getHeader("Content-Length")

        assert int(length) == len(PNG)


class TestAUserWithoutAProfilePicture:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("bob", email="bob@example.com")
        self.service = ProfilePortraitGet(portal, portal.REQUEST)
        self.service.params = ["bob"]

    def test_it_falls_through_to_the_member(self):
        """A Profile with an empty picture is not an answer. The member
        portrait is the fallback, and here there is none either, so this has
        to reach the base class's 404 rather than serve empty bytes."""
        self.service.render()

        assert self.service.request.response.getStatus() == 404


class TestAUserWithNoProfileAtAll:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.service = ProfilePortraitGet(portal, portal.REQUEST)
        self.service.params = ["nobody-here"]

    def test_the_base_class_still_answers(self):
        """The site's own ``admin`` and anything created before this layer
        was installed have no Profile, and must keep behaving exactly as
        stock Plone did."""
        self.service.render()

        assert self.service.request.response.getStatus() == 404


#: An SVG document: markup, and able to carry script.
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'


def store_member_portrait(userid: str, data: bytes, content_type: str) -> None:
    """Store a portrait on ``portal_memberdata``, the way PlonePAS keeps one.

    Raw storage, so the content type recorded is exactly the one under test.

    :param userid: Whose portrait.
    :param data: The image bytes.
    :param content_type: The type to record.
    """
    from OFS.Image import Image
    from plone import api

    portrait = Image(id=userid, title="", file=data, content_type=content_type)
    api.portal.get_tool("portal_memberdata")._setPortrait(portrait, userid)


class TestAUserWithAMemberPortrait:
    """No Profile, and a portrait on ``portal_memberdata``.

    The stock case, served by this class rather than by ``plone.restapi``'s:
    the base implementation's placeholder check raises on a site closed to
    anonymous visitors, which a public endpoint has to answer on.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        store_member_portrait("carol", PNG, "image/png")
        self.service = ProfilePortraitGet(portal, portal.REQUEST)
        self.service.params = ["carol"]

    def test_it_serves_the_member_portrait(self):
        """The bytes that were stored, not the shared placeholder."""
        assert read(self.service.render()) == PNG

    def test_it_answers_200_with_the_stored_type(self):
        """What a relying party checks before it uses the picture."""
        self.service.render()

        response = self.service.request.response
        assert response.getStatus() == 200
        assert response.getHeader("Content-Type") == "image/png"

    def test_an_image_is_shown_inline(self):
        """Only a type a browser must not render is sent as a download."""
        self.service.render()

        assert self.service.request.response.getHeader("Content-Disposition") is None


class TestAMemberPortraitABrowserMustNotRender:
    """A stored portrait whose type could run script if shown inline."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        store_member_portrait("carol", SVG, "image/svg+xml")
        self.service = ProfilePortraitGet(portal, portal.REQUEST)
        self.service.params = ["carol"]

    def test_it_is_sent_as_a_download(self):
        """The base class forces a download for it, and so does this."""
        self.service.render()

        disposition = self.service.request.response.getHeader("Content-Disposition")
        assert disposition.startswith("attachment;")
        assert "carol.svg" in disposition


class TestWhoIsAskedFor:
    """The path segments, read the way the base class reads them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.service = ProfilePortraitGet(portal, portal.REQUEST)

    def test_no_segment_asks_for_your_own(self):
        """The test user has no picture anywhere, so their own is a 404."""
        self.service.params = []

        self.service.render()

        assert self.service.request.response.getStatus() == 404

    def test_more_than_one_segment_is_the_base_class_error(self):
        """Its message is its own to write."""
        self.service.params = ["alice", "bob"]

        with pytest.raises(Exception, match="exactly zero"):
            self.service.render()
