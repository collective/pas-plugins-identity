"""Finding a Profile through the façade.

The interesting tests here are the ones about *absence*. ``get`` and
``get_current`` both answer ``None``, and the whole reason they are two
functions rather than one with a default is that a single function could not
tell the two kinds of ``None`` apart.

Creating a member is enough to get a Profile: the package mints one for every
account, so these tests ask for a member and let it happen rather than
building a Profile beside one and hoping the two agree about the userid.
"""

from pas.plugins.identity import api
from plone.app.testing import login
from plone.app.testing import logout

import pytest


class TestGet:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member) -> None:
        self.portal = portal
        self.userid = make_member("alice")

    def test_returns_the_profile(self):
        """The ordinary case."""
        profile = api.profile.get(self.userid)

        assert profile is not None
        assert profile.userid == self.userid

    def test_is_none_for_a_user_with_no_profile(self):
        """An account that predates the add-on and has not signed in since."""
        assert api.profile.get("nobody-at-all") is None

    def test_is_none_rather_than_the_callers_own_profile(self):
        """The failure mode the two-function split exists to prevent.

        A caller reading a userid out of catalog metadata that turns out to be
        missing passes ``None`` in. If this fell back to the current user it
        would hand back *their* Profile, every check downstream would pass,
        and the site would have told one person about another. In a package
        whose job is telling people apart, that is the worst direction for a
        silent fallback -- so the empty answer stays ``None`` even when there
        is an obvious current user to fall back to.
        """
        login(self.portal, "alice")
        assert api.profile.get_current() is not None  # a fallback had somewhere to go

        assert api.profile.get(None) is None
        assert api.profile.get("") is None

    def test_takes_its_argument(self):
        """Calling it with nothing is an error, not the current user."""
        with pytest.raises(TypeError):
            api.profile.get()


class TestGetCurrent:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member) -> None:
        self.portal = portal
        self.userid = make_member("alice")

    def test_returns_the_signed_in_users_profile(self):
        """The question :func:`get` deliberately cannot answer."""
        login(self.portal, "alice")

        profile = api.profile.get_current()

        assert profile is not None
        assert profile.userid == self.userid

    def test_is_none_for_an_anonymous_caller(self):
        """Anonymous is not an error here.

        A view asking "does the person reading this have a Profile" wants
        ``None`` for a visitor, not an exception it has to catch. The
        anonymous user's ``getId()`` is ``None``, so this lands in the same
        branch as "no userid" rather than needing a special case.
        """
        logout()

        assert api.profile.get_current() is None

    def test_takes_no_argument(self):
        """One question, no parameter to get wrong."""
        with pytest.raises(TypeError):
            api.profile.get_current("alice")


class TestGetOrCreate:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_mints_a_profile_for_a_userid_that_has_none(self):
        """What a first login does, offered to code that is not a login."""
        profile = api.profile.get_or_create("carol", "carol@example.com")

        assert profile is not None
        assert profile.userid == "carol"
        assert profile.login == "carol@example.com"

    def test_returns_the_existing_one_rather_than_a_second(self):
        """Called twice, one Profile.

        Two objects answering to one userid is the bug this prevents, and the
        second call's login argument is ignored rather than overwriting what
        is recorded.
        """
        first = api.profile.get_or_create("carol", "carol@example.com")
        second = api.profile.get_or_create("carol", "different@example.com")

        assert first.getId() == second.getId()
        assert second.login == "carol@example.com"

    def test_the_new_profile_is_findable_through_get(self):
        """The two halves of the namespace agree, which is the point of
        having them in one."""
        api.profile.get_or_create("dave", "dave@example.com")

        assert api.profile.get("dave") is not None


class TestTheProfileAnswersForItself:
    """Questions about one Profile are on the object, not in this namespace.

    The sorting rule the façade is built on: ``profile.email`` is a property
    because a Profile can answer it, while ``portrait.has_picture`` is a
    function because a user with no Profile can still have a picture.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_member) -> None:
        self.portal = portal
        self.userid = make_member("alice")
        self.profile = api.profile.get(self.userid)

    def test_the_address_is_a_property_of_the_profile(self):
        """No ``api.profile.email(userid)`` exists, and none should."""
        self.profile.emails = ("alice@example.com",)

        assert self.profile.email == "alice@example.com"
        assert not hasattr(api.profile, "email")

    def test_the_url_comes_from_the_object(self):
        """A ``profile_url(userid)`` on the façade would be two lookups where
        one will do, so the façade does not offer one."""
        assert api.profile.get(self.userid).absolute_url() == (
            self.profile.absolute_url()
        )
        assert not hasattr(api.profile, "url")

    def test_the_facade_returns_the_object_the_site_stores(self):
        """Not a copy, not a brain: the thing you can write to.

        Acquisition hands back a fresh wrapper each time, so this compares
        observable state rather than identity.
        """
        assert api.profile.get(self.userid).getPhysicalPath() == (
            self.profile.getPhysicalPath()
        )
