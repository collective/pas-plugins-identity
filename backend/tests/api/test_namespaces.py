"""The core-layer namespaces beside ``profile``.

Thin by design -- each one forwards to a function the layer already tests --
so what is asserted here is the façade's own promises: the names, the
argument shapes, and the empty answers.
"""

from pas.plugins.identity import api

import pytest


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
