"""``email`` is required on a Profile.

What used to live here as well -- that ``userid`` could not be rewritten
through a PATCH -- is now a property of the type rather than a rule enforced
on the way in: the userid *is* the object id, so there is no field to send.
See ``test_derived_ids.py``.
"""

from pas.plugins.identity.core.profile import IUserProfileSchema

import pytest


class TestEmailIsRequired:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_field_is_required(self):
        """A Profile exists to be the thing a person is reached and
        recognised by; the enumeration plugin, the property map and the
        magic-link join all read the address."""
        assert IUserProfileSchema["email"].required is True
