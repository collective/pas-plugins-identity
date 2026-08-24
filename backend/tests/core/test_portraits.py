"""Copying provider avatars into portrait storage.

The feature is off by default and the guards are the interesting part, so most
of these are about what is *refused*. A test suite that only proved the happy
path would be proving the wrong thing about a server-side fetcher on the login
path.

Nothing here reaches the network: ``requests.get`` is replaced, which is also
the honest way to test a size cap and a hostile content type.
"""

from io import BytesIO
from pas.plugins.identity.core import portraits
from pas.plugins.identity.core.pas import EXTRACTOR
from plone import api

import pytest


#: A real 1x1 PNG. Built rather than pasted so it is obvious what it is.
def _png() -> bytes:
    """Return the bytes of a small valid PNG.

    :returns: PNG bytes.
    """
    from PIL import Image as PILImage

    buffer = BytesIO()
    PILImage.new("RGB", (2, 2), (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeResponse:
    """Stand-in for a ``requests`` streaming response."""

    def __init__(
        self,
        data: bytes = b"",
        status_code: int = 200,
        content_type: str = "image/png",
    ) -> None:
        """Build the answer.

        :param data: Body bytes.
        :param status_code: HTTP status.
        :param content_type: Value of the ``Content-Type`` header.
        """
        self.data = data
        self.status_code = status_code
        self.headers = {"Content-Type": content_type} if content_type else {}

    def iter_content(self, chunk_size: int):
        """Yield the body in chunks.

        :param chunk_size: Bytes per chunk.
        :returns: Iterator of chunks.
        """
        for start in range(0, len(self.data), chunk_size):
            yield self.data[start : start + chunk_size]


@pytest.fixture
def answers(monkeypatch):
    """Return a helper that pins what the next fetch will get.

    :param monkeypatch: pytest's patcher.
    :returns: Callable taking a :class:`FakeResponse`.
    """
    calls: list[str] = []

    def pin(response: FakeResponse) -> list[str]:
        def fake_get(url, timeout=None, stream=False):
            """Record the URL and answer with the pinned response.

            :param url: URL requested.
            :param timeout: Ignored.
            :param stream: Ignored.
            :returns: The pinned response.
            """
            calls.append(url)
            return response

        monkeypatch.setattr(portraits.requests, "get", fake_get)
        return calls

    return pin


@pytest.fixture
def on(portal):
    """Switch portrait syncing on for this site.

    :param portal: The Plone site.
    :returns: The Plone site.
    """
    api.portal.set_registry_record(portraits.ENABLED_RECORD, True)
    return portal


def portrait_of(userid: str):
    """Return the stored portrait for a user, or ``None``.

    :param userid: Canonical Plone userid.
    :returns: The portrait image, or ``None``.
    """
    return api.portal.get_tool("portal_memberdata")._getPortrait(userid)


def sign_in(plugin, subject="s1", **claims) -> str:
    """Sign in through the plugin, which is what syncs the portrait.

    :param plugin: The identity plugin.
    :param subject: Provider-side subject; a new one is a new person.
    :param claims: Claims to send.
    :returns: The userid signed in as.
    """
    userid, _ = plugin.authenticateCredentials({
        "extractor": EXTRACTOR,
        "provider": "dex",
        "subject": subject,
        "claims": {"fullname": "Alice", "username": "alice", **claims},
    })
    return userid


class TestOffByDefault:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, answers) -> None:
        self.portal = portal
        self.answers = answers

    def test_disabled_in_a_fresh_site(self):
        """The feature exists; that is not the same as it being on."""
        assert portraits.enabled() is False

    def test_nothing_is_fetched_when_off(self):
        """Not even the request goes out."""
        calls = self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False
        assert calls == []

    def test_no_url_is_not_an_error(self):
        """A provider that sends no avatar is not a failure."""
        calls = self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "") is False
        assert calls == []


class TestGuards:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, answers, on) -> None:
        self.portal = portal
        self.answers = answers
        self.on = on

    def test_https_only(self):
        """A plain-HTTP URL is the easy way to aim this at an internal port."""
        calls = self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "http://cdn/a.png") is False
        assert calls == []

    def test_other_schemes_are_refused(self):
        """``file://`` would read the backend's disk."""
        calls = self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "file:///etc/passwd") is False
        assert calls == []

    def test_non_200_is_refused(self):
        """An error page is not an avatar."""
        self.answers(FakeResponse(b"nope", status_code=404))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False

    def test_non_image_content_type_is_refused(self):
        """What the server says it is sending has to be an image."""
        self.answers(FakeResponse(_png(), content_type="text/html"))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False

    def test_missing_content_type_is_refused(self):
        """Absent is not "probably fine"."""
        self.answers(FakeResponse(_png(), content_type=""))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False

    def test_oversized_body_is_refused(self):
        """Counted off the stream, not taken from a header a server can lie
        about."""
        self.answers(FakeResponse(b"\x00" * (portraits.MAX_BYTES + 1)))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False

    def test_a_broken_image_does_not_break_the_login(self):
        """Bytes that claim to be a PNG and are not."""
        self.answers(FakeResponse(b"not an image at all"))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False

    def test_a_network_failure_does_not_break_the_login(self, monkeypatch):
        """The whole point of swallowing everything."""

        def explode(url, timeout=None, stream=False):
            """Fail the way DNS does.

            :param url: URL requested.
            :param timeout: Ignored.
            :param stream: Ignored.
            :raises OSError: Always.
            """
            raise OSError("name or service not known")

        monkeypatch.setattr(portraits.requests, "get", explode)

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is False


class TestStoring:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, answers, on) -> None:
        self.portal = portal
        self.answers = answers
        self.on = on

    def test_a_good_avatar_is_stored(self):
        """The happy path, once every guard is satisfied."""
        self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "https://cdn/a.png") is True
        assert portrait_of("alice") is not None

    def test_it_replaces_a_previous_portrait(self):
        """Storing twice must not raise on the duplicate id."""
        self.answers(FakeResponse(_png()))
        portraits.sync_portrait("alice", "https://cdn/a.png")

        self.answers(FakeResponse(_png()))

        assert portraits.sync_portrait("alice", "https://cdn/b.png") is True


class TestThroughTheSync:
    """Signing in: when a fetch is attempted at all. No [profile] layer here
    -- portraits belong to the member, so they work without it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, answers, on) -> None:
        self.portal = portal
        self.plugin = plugin
        self.answers = answers
        self.on = on

    def test_first_login_fetches_once(self):
        """A new avatar is worth a request."""
        calls = self.answers(FakeResponse(_png()))

        sign_in(self.plugin, picture_url="https://cdn/a.png")

        assert calls == ["https://cdn/a.png"]

    def test_second_login_with_the_same_url_does_not_refetch(self):
        """This is the one part of signing in that touches the network, and
        it runs while somebody waits for a page."""
        calls = self.answers(FakeResponse(_png()))
        sign_in(self.plugin, picture_url="https://cdn/a.png")

        sign_in(self.plugin, picture_url="https://cdn/a.png")

        assert calls == ["https://cdn/a.png"]

    def test_a_changed_url_is_refetched(self):
        """Changing your avatar at the provider should change it here."""
        calls = self.answers(FakeResponse(_png()))
        sign_in(self.plugin, picture_url="https://cdn/a.png")

        sign_in(self.plugin, picture_url="https://cdn/b.png")

        assert calls == ["https://cdn/a.png", "https://cdn/b.png"]

    def test_a_failed_url_is_not_retried(self):
        """One bad avatar must not become a permanent tax on that user's
        sign-in."""
        calls = self.answers(FakeResponse(b"", status_code=500))
        sign_in(self.plugin, picture_url="https://cdn/a.png")

        sign_in(self.plugin, picture_url="https://cdn/a.png")

        # One attempt, not two: the claims snapshot remembers the URL whether
        # or not the fetch worked, so a URL that failed once is not tried
        # again on every login.
        assert calls == ["https://cdn/a.png"]

    def test_no_picture_claim_is_a_no_op(self):
        """Most providers send none."""
        calls = self.answers(FakeResponse(_png()))

        sign_in(self.plugin)

        assert calls == []


class TestTheFeatureOff:
    """The default path, which is the one nearly every site is on."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, answers) -> None:
        self.portal = portal
        self.plugin = plugin
        self.answers = answers

    def test_login_still_works(self):
        """No fetch, and the sign-in is unaffected."""
        calls = self.answers(FakeResponse(_png()))

        userid = sign_in(self.plugin, picture_url="https://cdn/a.png")

        assert calls == []
        assert userid
