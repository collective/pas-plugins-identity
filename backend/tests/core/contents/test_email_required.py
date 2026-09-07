"""``emails`` is required on a Profile, wherever it is declared.

What used to live here as well -- that ``userid`` could not be rewritten
through a PATCH -- is now a property of the type rather than a rule enforced
on the way in: the userid *is* the object id, so there is no field to send.
See ``test_derived_ids.py``.

The fields moved to
:class:`~pas.plugins.identity.core.behaviors.email.IEmailAddresses`, so the
schema assertions below are asked of the behavior. On their own they would
prove only that a schema somewhere says ``required``: a behavior the FTI does
not enable is a schema nothing reaches. ``TestTheProfileHasThem`` is the half
that matters.
"""

from pas.plugins.identity.core.behaviors.email import IEmailAddresses
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.dexterity.utils import iterSchemata

import pytest


class TestEmailIsRequired:
    def test_the_field_is_required(self):
        """A Profile exists to be the thing a person is reached and
        recognised by; the enumeration plugin, the property map and the
        magic-link join all read the address."""
        assert IEmailAddresses["emails"].required is True

    def test_the_derived_field_is_not(self):
        """``email`` is computed from the list, so requiring it would be
        requiring the same thing twice -- and it is read-only, so a form
        insisting on it would insist on something nobody can type."""
        assert IEmailAddresses["email"].required is False
        assert IEmailAddresses["email"].readonly is True


class TestTheProfileHasThem:
    """The behavior reaches the shipped type.

    Moving a field to a behavior is silent in both directions: the schema
    still says what it always said, and a type that does not enable the
    behavior simply has no such field. Only the FTI says which is true here.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.fti = api.portal.get_tool("portal_types")[PROFILE_PORTAL_TYPE]

    def test_the_type_enables_the_behavior(self):
        assert "pas.plugins.identity.email_addresses" in self.fti.behaviors

    def test_a_profile_reaches_the_fields(self):
        """Through ``iterSchemata``, which is what every form, the
        deserializer and ``completeness`` walk."""
        profile = api.content.create(
            container=self.portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="dana",
            userid="dana",
            login="dana",
            emails=("dana@example.com",),
        )
        declared = {name for schema in iterSchemata(profile) for name in schema.names()}
        assert {"emails", "email"} <= declared
        assert profile.emails == ("dana@example.com",)
        assert profile.email == "dana@example.com"
