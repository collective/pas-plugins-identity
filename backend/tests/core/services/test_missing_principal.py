"""A login that succeeds and names an account nothing can serve.

PAS answers with a principal whether or not anything became the record behind
it. On an ordinary site core writes a ``source_users`` row; on a site that
keeps its users as content the object *is* the account and creating it is the
site's own job -- so a site with the records set and nothing claiming its
users authenticates people into accounts that do not exist.

Érico hit it signing in with Google (2026-08-28). Every later lookup of the
userid returned ``None``, and the first line to dereference one was
``mint_token``: ``AttributeError: 'NoneType' object has no attribute
'getId'``, from a traceback naming neither the user nor the reason. The
warning that says exactly what happened was two lines above it in the log and
looked unrelated.

The state is a site configuration this package cannot fix from inside a
login. What it can do is say so.
"""

from pas.plugins.identity.core.interfaces import PrincipalUnavailable
from pas.plugins.identity.core.services.jwt import mint_token

import pytest


class TestMintingForAUserThatIsNotThere:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_it_raises_rather_than_dereferencing_none(self):
        """The bug: an AttributeError from whichever line touched the user
        first, which happened to be this one."""
        with pytest.raises(PrincipalUnavailable):
            mint_token("nobody-by-that-name")

    def test_the_message_names_the_userid(self):
        """An operator reading the log needs to know which login it was."""
        with pytest.raises(PrincipalUnavailable, match="nobody-by-that-name"):
            mint_token("nobody-by-that-name")

    def test_the_message_names_the_cause(self):
        """And what to go and look at -- the record nothing created."""
        with pytest.raises(PrincipalUnavailable, match="content object"):
            mint_token("nobody-by-that-name")

    def test_a_real_user_still_gets_a_token(self):
        """The guard is about a userid nothing resolves, not about tokens."""
        from plone.app.testing import TEST_USER_ID

        assert mint_token(TEST_USER_ID)

    def test_it_is_not_confused_with_a_missing_jwt_plugin(self):
        """`None` means "this site cannot mint tokens at all", which sends
        whoever reads it to a different control panel."""
        with pytest.raises(PrincipalUnavailable):
            mint_token("nobody-by-that-name")
