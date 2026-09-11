"""The core-layer namespaces beside ``profile``.

Thin by design -- each one forwards to a function the layer already tests --
so what is asserted here is the façade's own promises: the names, the
argument shapes, and the empty answers.
"""

from io import BytesIO
from pas.plugins.identity import api
from pas.plugins.identity.core import portraits
from plone import api as plone_api

import pytest


def png() -> bytes:
    """Return the bytes of a small valid PNG.

    :returns: PNG bytes.
    """
    from PIL import Image as PILImage

    buffer = BytesIO()
    PILImage.new("RGB", (2, 2), (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeImageResponse:
    """A ``requests`` streaming response carrying a PNG."""

    status_code = 200
    headers = {"Content-Type": "image/png"}  # noqa: RUF012

    def iter_content(self, chunk_size: int):
        """Yield the whole body at once.

        :param chunk_size: Ignored.
        :returns: Iterator over one chunk.
        """
        yield png()


class TestPortrait:
    """Keyed by userid, not by Profile, and the docstring says why.

    A user with no Profile can still have a member portrait, so
    ``profile.has_picture()`` could not express an answer of ``True``.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member) -> None:
        self.portal = portal
        self.userid = make_member("alice")

    def test_a_fresh_account_has_no_picture(self):
        """False rather than None: this is a yes-or-no question, and a
        caller should not have to treat "no picture" as "no answer"."""
        assert api.portrait.has_picture(self.userid) is False

    def test_an_unknown_user_has_no_picture(self):
        """No account, no picture, no exception."""
        assert api.portrait.has_picture("nobody-at-all") is False

    def test_the_url_is_none_when_there_is_no_picture(self):
        """``None`` rather than an empty string, so a template can test it
        without knowing which falsy value to expect."""
        assert api.portrait.get_url(self.userid) is None

    def test_the_two_questions_are_not_the_same_one(self):
        """:func:`has_picture` also looks in ``portal_memberdata``, which is
        why it is not simply ``get_url(...) is not None``."""
        assert api.portrait.has_picture is not api.portrait.get_url


class TestWritingAPortrait:
    """The two writes, one for a caller holding bytes and one holding a URL.

    What each does with a picture is tested where it is implemented. These
    hold the façade's promises: that bytes become a picture, and that the URL
    form answers ``False`` instead of raising, whatever stopped it.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member, monkeypatch) -> None:
        self.portal = portal
        self.userid = make_member("alice")
        self.fetched: list[str] = []

        def fake_get(url, timeout=None, stream=False):
            self.fetched.append(url)
            return FakeImageResponse()

        monkeypatch.setattr(portraits.requests, "get", fake_get)

    def switch_syncing_on(self) -> None:
        """Turn on the site-wide switch every fetch waits for."""
        plone_api.portal.set_registry_record(portraits.ENABLED_RECORD, True)

    def test_bytes_a_caller_holds_become_the_picture(self):
        api.portrait.store(self.userid, png())

        assert api.portrait.has_picture(self.userid) is True

    def test_nothing_is_fetched_while_syncing_is_off(self):
        """The switch is the site's, and an import does not get to skip it."""
        stored = api.portrait.sync_portrait(self.userid, "https://example.com/a.png")

        assert (stored, self.fetched) == (False, [])

    def test_a_refused_url_answers_false_rather_than_raising(self):
        """Plain HTTP, not allowed: a refusal, reported as ``False``."""
        self.switch_syncing_on()

        stored = api.portrait.sync_portrait(self.userid, "http://example.com/a.png")

        assert (stored, self.fetched) == (False, [])

    def test_a_fetched_picture_is_stored(self):
        self.switch_syncing_on()

        stored = api.portrait.sync_portrait(self.userid, "https://example.com/a.png")

        assert stored is True
        assert api.portrait.has_picture(self.userid) is True


class TestProvider:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_no_providers_is_an_empty_list(self):
        """Not ``None``: a caller iterating over the result should not have
        to guard first."""
        assert api.provider.get_all() == []

    def test_an_unknown_provider_is_none(self):
        """A lookup, so it answers ``None`` rather than raising."""
        assert api.provider.get("no-such-provider") is None

    def test_the_configured_provider_is_found(self, configured_provider):
        """The ordinary case, read back through the façade."""
        provider = api.provider.get(configured_provider)

        assert provider is not None
        assert provider.provider_id == configured_provider

    def test_it_is_the_same_object_the_list_carries(self, configured_provider):
        """One provider, one answer, whichever way it is asked for."""
        listed = [p.provider_id for p in api.provider.get_all()]

        assert configured_provider in listed

    def test_the_plugin_is_reachable(self):
        """A downstream package asking "is this installed here" should not
        have to know the plugin id or reach into ``acl_users``."""
        assert api.provider.plugin() is not None
