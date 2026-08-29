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
